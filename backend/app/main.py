"""
FastAPI Backend Application Entry Point (Phase 5)

Serves:
- REST API for Multi-Agent Travel Planning
- PDF Report Generation & Download
- Conversational Itinerary Assistant
- Static UI Frontend Hosting
"""

import sys
import os
import uuid
import json
import math
from typing import Dict, Any, Optional

# Ensure application path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models.schemas import TripRequest, TripPlanResponse, ChatRequest, ChatResponse
from app.models.database import DatabaseManager
from app.multi_agent.supervisor import TravelManagerSupervisor
from app.core.memory import MemoryStore
from app.services.pdf_service import TravelPDFGenerator
from app.services.llm_service import (
    GeminiLLMService,
    LLMInvalidResponseError,
    LLMServiceError
)
from app.config import settings

# In-memory and persistent SQLite database (Phase 2)
TRIP_STORAGE: Dict[str, Dict[str, Any]] = {}
TRIP_OWNERS: Dict[str, str] = {}
db_manager = DatabaseManager(settings.DATABASE_PATH)



app = FastAPI(
    title="AI Travel Planning Agent API",
    description="Agentic AI system coordinating multi-agent workflows for intelligent travel planning.",
    version="1.0.0"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared singletons
supervisor = TravelManagerSupervisor()
memory_store = MemoryStore()
pdf_generator = TravelPDFGenerator()
llm_service = GeminiLLMService(
    api_key=settings.GEMINI_API_KEY,
    model=settings.GEMINI_MODEL
)


@app.get("/api/health")
def health_check():
    """System health check and diagnostic status."""
    return {
        "status": "online",
        "service": "AI Travel Planning Agent",
        "version": "1.0.0",
        "tools_loaded": 4,
        "agents_active": 6,
        "memory_store": "active"
    }


@app.post("/api/trip/plan", response_model=TripPlanResponse)
def plan_trip(request: TripRequest):
    """
    Triggers multi-agent collaboration to construct a personalized trip itinerary.
    """
    trip_id = str(uuid.uuid4())
    
    # Check and record user preferences in persistent memory (📘 L4)
    if request.travel_preferences:
        memory_store.set_preference(request.user_id, "travel_interests", request.travel_preferences)
    memory_store.set_preference(request.user_id, "preferred_hotel_tier", request.accommodation_type)

    # Invoke Multi-Agent Supervisor (📘 L6)
    team_result = supervisor.plan_trip(
        query=f"Plan a {request.duration_days}-day trip to {request.destination} with budget ${request.budget}",
        destination=request.destination,
        duration_days=request.duration_days,
        budget=request.budget,
        travelers=request.travelers_count
    )

    # Prepare hotels list safely
    hotels_list = []
    if team_result.get("hotel_data") and team_result["hotel_data"].get("hotels"):
        hotels_list = team_result["hotel_data"]["hotels"]

    # Package response
    response_data = {
        "trip_id": trip_id,
        "destination": team_result["destination"],
        "duration_days": team_result["duration_days"],
        "budget": team_result["budget"],
        "travelers": team_result["travelers"],
        "weather_summary": team_result.get("weather_data") or {},
        "hotels": hotels_list,
        "budget_breakdown": team_result.get("budget_breakdown") or {},
        "daily_itinerary": team_result.get("daily_schedule") or [],
        "final_report": team_result.get("final_report") or "Travel plan generated.",
        "team_logs": team_result.get("team_logs") or [],
        "status": "success"
    }

    # Save to storage and database for retrieval & PDF export
    TRIP_STORAGE[trip_id] = {
        **response_data,
        "hotel_data": team_result.get("hotel_data") or {},
        "weather_data": team_result.get("weather_data") or {}
    }
    TRIP_OWNERS[trip_id] = request.user_id
    db_manager.save_trip(trip_id, request.user_id, response_data)
    db_manager.set_user_memory(request.user_id, "last_trip_id", trip_id)

    # Record completed trip into long-term user memory (📘 L4)
    memory_store.record_trip(
        user_id=request.user_id,
        destination=request.destination,
        summary=f"{request.duration_days}-day trip",
        total_spent=response_data["budget_breakdown"].get("total_allocated_usd", request.budget)
    )

    return response_data


@app.get("/api/trip/{trip_id}")
def get_trip(trip_id: str):
    """Retrieves a previously generated trip plan by trip_id."""
    if trip_id in TRIP_STORAGE:
        return TRIP_STORAGE[trip_id]
    db_trip = db_manager.get_trip(trip_id)
    if db_trip:
        return db_trip
    raise HTTPException(status_code=404, detail="Trip record not found.")



@app.get("/api/trip/{trip_id}/pdf")
def download_trip_pdf(trip_id: str):
    """
    Generates and downloads a publication-ready PDF travel report (Phase 6).
    """
    if trip_id not in TRIP_STORAGE:
        raise HTTPException(status_code=404, detail="Trip record not found.")

    trip_data = TRIP_STORAGE[trip_id]
    pdf_bytes = pdf_generator.generate_pdf(trip_data)

    dest_safe = trip_data.get("destination", "Trip").replace(" ", "_")
    filename = f"Itinerary_{dest_safe}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_agent(chat_req: ChatRequest):
    """Answer naturally with Gemini, scoped trip context, and persisted conversation history."""
    plan = None
    if chat_req.trip_id:
        plan = TRIP_STORAGE.get(chat_req.trip_id)
        if plan is None:
            plan = db_manager.get_trip(chat_req.trip_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Trip record not found.")

        owner_id = TRIP_OWNERS.get(chat_req.trip_id) or plan.get("user_id")
        if owner_id and owner_id != chat_req.user_id:
            raise HTTPException(status_code=404, detail="Trip record not found.")

    history = db_manager.get_chat_history(chat_req.user_id, chat_req.trip_id)
    trip_context = _chat_trip_context(plan, chat_req)
    prompt = (
        "You are the conversational AI travel assistant for Dream Line Travels. "
        "Respond naturally to greetings, capability questions, destination questions, and follow-ups. "
        "Use the supplied conversation and trip data to answer questions about the itinerary, travelers, "
        "duration, destination, and budget. Give useful attractions, restaurant, and hotel suggestions; "
        "do not claim live availability or prices unless supplied in context. Suggest practical lower-cost "
        "alternatives when asked. Never claim that a trip was changed unless you return a concrete "
        "updated_plan. If there is no active trip, explain that a trip must be generated before making "
        "itinerary changes.\n\n"
        "Return exactly one JSON object with string field 'reply' and field 'updated_plan'. "
        "Set updated_plan to null for ordinary questions. For a requested trip change, return only the "
        "changed fields in updated_plan, using only these keys: destination, duration_days, budget, "
        "travelers, weather_summary, hotels, budget_breakdown, daily_itinerary, final_report. "
        "For destination changes, set the new destination; the server will rebuild the destination-specific "
        "itinerary. For other itinerary changes, provide concrete replacement values. Do not wrap JSON "
        "in markdown.\n\n"
        f"Current trip data: {json.dumps(trip_context, ensure_ascii=False)}\n"
        f"Conversation history: {json.dumps(history, ensure_ascii=False)}\n"
        f"Current user message: {chat_req.message}"
    )

    try:
        raw_response = llm_service.generate(
            prompt,
            temperature=0.3,
            allow_offline_fallback=False
        )
        result = _parse_chat_result(raw_response)
        updated_plan = _apply_chat_plan_update(
            result["updated_plan"],
            plan,
            chat_req
        )
    except LLMServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    db_manager.save_chat_turn(
        chat_req.user_id,
        chat_req.trip_id,
        chat_req.message,
        result["reply"]
    )
    return ChatResponse(
        reply=result["reply"],
        updated_plan=updated_plan,
        agent_thoughts=["Gemini generated the response using this trip conversation."]
    )


def _chat_trip_context(
    plan: Optional[Dict[str, Any]],
    chat_req: ChatRequest
) -> Dict[str, Any]:
    if plan is None:
        return {
            "destination": chat_req.destination,
            "duration_days": chat_req.duration_days,
            "trip_exists": False
        }
    return {
        key: plan.get(key)
        for key in (
            "destination",
            "duration_days",
            "budget",
            "travelers",
            "weather_summary",
            "hotels",
            "budget_breakdown",
            "daily_itinerary",
            "final_report"
        )
    }


def _parse_chat_result(raw_response: str) -> Dict[str, Any]:
    """Parse and validate the model's required JSON response."""
    try:
        json_start = raw_response.index("{")
        result, _ = json.JSONDecoder().raw_decode(raw_response[json_start:])
    except (ValueError, json.JSONDecodeError) as exc:
        raise LLMInvalidResponseError(
            "Gemini returned an invalid chat response. Please try again."
        ) from exc

    if not isinstance(result, dict):
        raise LLMInvalidResponseError("Gemini returned an invalid chat response.")
    reply = result.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise LLMInvalidResponseError("Gemini returned an empty chat answer.")
    if "updated_plan" not in result:
        raise LLMInvalidResponseError(
            "Gemini did not return the required itinerary update field."
        )

    changes = result["updated_plan"]
    if changes is not None:
        if not isinstance(changes, dict):
            raise LLMInvalidResponseError("Gemini returned an invalid itinerary update.")
        allowed_fields = {
            "destination", "duration_days", "budget", "travelers",
            "weather_summary", "hotels", "budget_breakdown",
            "daily_itinerary", "final_report"
        }
        if not changes or set(changes) - allowed_fields:
            raise LLMInvalidResponseError("Gemini returned an invalid itinerary update.")
        if "destination" in changes and (
            not isinstance(changes["destination"], str) or not changes["destination"].strip()
        ):
            raise LLMInvalidResponseError("Gemini returned an invalid destination.")
        if "duration_days" in changes and (
            isinstance(changes["duration_days"], bool)
            or not isinstance(changes["duration_days"], int)
            or not 1 <= changes["duration_days"] <= 14
        ):
            raise LLMInvalidResponseError("Gemini returned an invalid trip duration.")
        if "budget" in changes and not _is_valid_budget(changes["budget"]):
            raise LLMInvalidResponseError("Gemini returned an invalid trip budget.")
        if "travelers" in changes and (
            isinstance(changes["travelers"], bool)
            or not isinstance(changes["travelers"], int)
            or changes["travelers"] < 1
        ):
            raise LLMInvalidResponseError("Gemini returned an invalid traveler count.")
        if "weather_summary" in changes and not isinstance(changes["weather_summary"], dict):
            raise LLMInvalidResponseError("Gemini returned invalid weather information.")
        if "hotels" in changes and (
            not isinstance(changes["hotels"], list)
            or any(not isinstance(hotel, dict) for hotel in changes["hotels"])
        ):
            raise LLMInvalidResponseError("Gemini returned invalid hotel recommendations.")
        if "budget_breakdown" in changes and not isinstance(changes["budget_breakdown"], dict):
            raise LLMInvalidResponseError("Gemini returned an invalid budget breakdown.")
        if "daily_itinerary" in changes and not _is_valid_itinerary(changes["daily_itinerary"]):
            raise LLMInvalidResponseError("Gemini returned an invalid daily itinerary.")
        if "final_report" in changes and not isinstance(changes["final_report"], str):
            raise LLMInvalidResponseError("Gemini returned an invalid itinerary summary.")

    return {"reply": reply.strip(), "updated_plan": changes}


def _is_valid_itinerary(itinerary: Any) -> bool:
    if not isinstance(itinerary, list):
        return False
    for day in itinerary:
        if not isinstance(day, dict) or not isinstance(day.get("slots"), dict):
            return False
        if any(not isinstance(day["slots"].get(slot), str) for slot in ("morning", "afternoon", "evening")):
            return False
    return True


def _is_valid_budget(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _apply_chat_plan_update(
    changes: Optional[Dict[str, Any]],
    plan: Optional[Dict[str, Any]],
    chat_req: ChatRequest
) -> Optional[Dict[str, Any]]:
    if changes is None:
        return None
    if plan is None:
        raise LLMInvalidResponseError(
            "Gemini attempted to change a trip, but no active trip was provided."
        )

    new_destination = changes.get("destination", plan.get("destination", chat_req.destination))
    if new_destination.strip().casefold() != str(plan.get("destination", "")).casefold():
        duration_days = changes.get("duration_days", plan.get("duration_days", chat_req.duration_days))
        budget = changes.get("budget", plan.get("budget", 1000.0))
        travelers = changes.get("travelers", plan.get("travelers", 1))
        team_result = supervisor.plan_trip(
            query=f"Rebuild the existing itinerary for {new_destination}",
            destination=new_destination.strip(),
            duration_days=duration_days,
            budget=budget,
            travelers=travelers
        )
        updated = {
            **plan,
            "destination": team_result["destination"],
            "duration_days": team_result["duration_days"],
            "budget": team_result["budget"],
            "travelers": team_result["travelers"],
            "weather_summary": team_result.get("weather_data") or {},
            "hotels": (team_result.get("hotel_data") or {}).get("hotels", []),
            "budget_breakdown": team_result.get("budget_breakdown") or {},
            "daily_itinerary": team_result.get("daily_schedule") or [],
            "final_report": team_result.get("final_report") or "",
            "team_logs": team_result.get("team_logs") or []
        }
    else:
        updated = {**plan, **changes}
        if all(updated.get(key) == plan.get(key) for key in changes):
            raise LLMInvalidResponseError(
                "Gemini did not provide a substantive itinerary change."
            )

    updated["trip_id"] = chat_req.trip_id
    user_id = chat_req.user_id
    TRIP_STORAGE[chat_req.trip_id] = updated
    db_manager.save_trip(chat_req.trip_id, user_id, updated)
    return updated


# Mount static frontend directory if present
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
