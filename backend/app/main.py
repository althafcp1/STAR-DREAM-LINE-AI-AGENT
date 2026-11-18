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
from app.services.currency_service import convert as currency_convert, format_conversion_reply, get_rates, SUPPORTED as SUPPORTED_CURRENCIES

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
        "service": "DreamLine AI Travel Agent",
        "version": "1.0.0",
        "tools_loaded": 4,
        "agents_active": 6,
        "memory_store": "active",
        "gemini_configured": llm_service.is_configured()
    }


@app.get("/api/check-key")
def check_api_key():
    """Diagnostic: check whether Gemini API key is loaded and model configured (never exposes keys)."""
    configured = llm_service.is_configured()
    return {
        "gemini_configured": configured,
        "gemini_model": llm_service.model,
        "message": (
            f"Gemini API key is loaded. Configured model: '{llm_service.model}'." if configured
            else "GEMINI_API_KEY is not set or still a placeholder. "
                 "Edit backend/.env and add your real API key from https://aistudio.google.com/apikey"
        )
    }


@app.get("/api/test-gemini")
def test_gemini_connection():
    """Minimal live Gemini connection test using the configured model."""
    if not llm_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Set a valid GEMINI_API_KEY in backend/.env or environment."
        )
    try:
        reply = llm_service.generate("Reply with 'pong' if you hear me.", allow_offline_fallback=False)
        return {
            "status": "success",
            "model": llm_service.model,
            "response": reply
        }
    except LLMServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/api/currency/rates")
def get_currency_rates():
    """Return current USD-based exchange rates and their source."""
    try:
        rates, source, fetched_at = get_rates()
        import datetime
        return {
            "base": "USD",
            "rates": {k: rates[k] for k in SUPPORTED_CURRENCIES if k in rates},
            "source": source,
            "fetched_at": datetime.datetime.fromtimestamp(fetched_at).strftime("%Y-%m-%d %H:%M UTC"),
            "supported_currencies": SUPPORTED_CURRENCIES
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not fetch exchange rates: {exc}")


@app.get("/api/currency/convert")
def convert_currency(amount: float, from_currency: str, to_currency: str):
    """Convert an amount between supported currencies."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    result = currency_convert(amount, from_currency, to_currency)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


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

    lang = getattr(chat_req, "language", "en") or "en"
    history = db_manager.get_chat_history(chat_req.user_id, chat_req.trip_id)
    trip_context = _chat_trip_context(plan, chat_req)

    # ── Currency detection: handle conversion questions directly ──────────
    currency_context = _detect_and_convert_currency(chat_req.message, lang)

    arabic_instruction = ""
    if lang == "ar":
        arabic_instruction = (
            "IMPORTANT: The user has selected Arabic language. "
            "Respond in professional, friendly Modern Standard Arabic (Gulf Arabic style). "
            "Use AED (درهم) for UAE prices and INR (روبية) for India prices. "
            "Keep all JSON keys in English.\n\n"
        )

    prompt = (
        "You are DreamLine AI Travel Assistant – a professional, friendly, and knowledgeable "
        "travel consultant for Dream Line Travels.\n"
        "Tagline: 'Your Intelligent Travel Companion'.\n\n"

        "EXPERTISE:\n"
        "1. UAE TRAVEL: Dubai (Burj Khalifa, Dubai Mall, Desert Safari, Palm Jumeirah, Dubai Creek, "
        "Gold Souk, Dubai Frame, Miracle Garden), Abu Dhabi (Sheikh Zayed Grand Mosque, Louvre, "
        "Ferrari World, Yas Island, Corniche), Sharjah (Blue Souk, Al Noor Island, Heritage Area), "
        "Ras Al Khaimah, Fujairah, Ajman, Umm Al Quwain.\n"
        "2. INDIA TRAVEL: Kerala (Munnar tea gardens, Alleppey backwaters, Wayanad forests, "
        "Kochi Fort, Kozhikode beach), Goa (beaches, spice plantations, Portuguese heritage), "
        "Rajasthan (Jaipur Pink City, Udaipur lakes, Jodhpur Blue City), Delhi (Red Fort, "
        "Qutub Minar, Chandni Chowk), Mumbai (Gateway of India, Marine Drive, Bollywood), "
        "Tamil Nadu (Ooty, Kodaikanal, Madurai Meenakshi Temple), Karnataka (Coorg, Mysore), "
        "Himachal Pradesh (Shimla, Manali), and all other Indian destinations.\n"
        "3. INDIA ↔ UAE TRAVEL: Flight routes, visa requirements, travel tips for both markets.\n"
        "4. CURRENCIES: INR (₹) for India, AED (د.إ) for UAE, USD ($) internationally. "
        "Always label prices as ESTIMATED.\n\n"

        "CURRENCY CONVERSION CAPABILITY:\n"
        f"{currency_context}\n\n"

        "RULES:\n"
        "- Ask follow-up questions when destination, budget, duration or traveller count is missing.\n"
        "- Never claim a hotel, flight or tour is booked unless a real system confirms it.\n"
        "- Distinguish estimated prices from actual prices clearly.\n"
        "- Support mixed Arabic-English messages.\n\n"
        + arabic_instruction +

        "RESPONSE FORMAT:\n"
        "Return exactly one JSON object with no markdown fences:\n"
        '{"reply": "<your answer>", "updated_plan": null}\n\n'
        "Rules:\n"
        "- 'reply': non-empty string, your full helpful answer.\n"
        "- 'updated_plan': null for most replies; a dict only if the user explicitly asks to change "
        "the current trip itinerary (allowed keys: destination, duration_days, budget, travelers, "
        "weather_summary, hotels, budget_breakdown, daily_itinerary, final_report).\n"
        "- Do NOT wrap JSON in ```json``` markdown.\n"
        "- Always reply helpfully. Never refuse.\n\n"

        f"Current trip: {json.dumps(trip_context, ensure_ascii=False)}\n"
        f"Recent history (last 10): {json.dumps(history[-10:] if history else [], ensure_ascii=False)}\n"
        f"User message: {chat_req.message}"
    )

    try:
        raw_response = llm_service.generate(
            prompt,
            temperature=0.4,
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
        agent_thoughts=["DreamLine AI generated this response via Gemini."]
    )


def _detect_and_convert_currency(message: str, lang: str = "en") -> str:
    """
    Detect currency conversion intent in the message and pre-compute the result
    so the AI can include it accurately in the reply.
    """
    import re
    msg_lower = message.lower()

    # Patterns: "convert 100 usd to inr", "100 dollars in rupees", "$500 in INR", etc.
    patterns = [
        r"(\d[\d,]*\.?\d*)\s*(usd|dollar[s]?|\$)\s*(?:to|in|into|=)\s*(inr|rupee[s]?|₹)",
        r"(\d[\d,]*\.?\d*)\s*(inr|rupee[s]?|₹)\s*(?:to|in|into|=)\s*(usd|dollar[s]?|\$)",
        r"(\d[\d,]*\.?\d*)\s*(aed|dirham[s]?)\s*(?:to|in|into|=)\s*(inr|rupee[s]?|₹)",
        r"(\d[\d,]*\.?\d*)\s*(inr|rupee[s]?|₹)\s*(?:to|in|into|=)\s*(aed|dirham[s]?)",
        r"(\d[\d,]*\.?\d*)\s*(usd|dollar[s]?|\$)\s*(?:to|in|into|=)\s*(aed|dirham[s]?)",
        r"(\d[\d,]*\.?\d*)\s*(aed|dirham[s]?)\s*(?:to|in|into|=)\s*(usd|dollar[s]?|\$)",
        r"convert\s+(\d[\d,]*\.?\d*)\s*(usd|inr|aed|dollar[s]?|rupee[s]?|dirham[s]?)\s+(?:to|into)\s+(usd|inr|aed|dollar[s]?|rupee[s]?|dirham[s]?)",
    ]

    sym_map = {
        "usd": "USD", "dollar": "USD", "dollars": "USD", "$": "USD",
        "inr": "INR", "rupee": "INR", "rupees": "INR", "₹": "INR",
        "aed": "AED", "dirham": "AED", "dirhams": "AED",
    }

    for pattern in patterns:
        m = re.search(pattern, msg_lower)
        if m:
            groups = m.groups()
            amount_str = groups[0].replace(",", "")
            from_raw   = groups[1]
            to_raw     = groups[2]
            try:
                amount = float(amount_str)
                from_c = sym_map.get(from_raw, from_raw.upper())
                to_c   = sym_map.get(to_raw,   to_raw.upper())
                result = currency_convert(amount, from_c, to_c)
                if "error" not in result:
                    return (
                        f"CURRENCY CONVERSION RESULT (pre-computed for accuracy):\n"
                        f"{format_conversion_reply(result, lang)}\n"
                        "Include this exact conversion in your reply."
                    )
            except ValueError:
                pass

    return "No currency conversion detected in this message."


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
    """Parse Gemini's response – handles JSON, markdown-fenced JSON, and plain text fallback."""
    cleaned = raw_response.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    # Try to find and parse a JSON object
    result = None
    try:
        brace_start = cleaned.index("{")
        result, _ = json.JSONDecoder().raw_decode(cleaned[brace_start:])
    except (ValueError, json.JSONDecodeError):
        result = None

    # If JSON has a valid 'reply' field, use it with optional updated_plan validation
    if isinstance(result, dict) and isinstance(result.get("reply"), str) and result["reply"].strip():
        reply = result["reply"].strip()
        changes = result.get("updated_plan", None)

        # Validate updated_plan only if it is non-null
        if changes is not None:
            if not isinstance(changes, dict):
                changes = None  # ignore bad update, keep the reply
            else:
                allowed_fields = {
                    "destination", "duration_days", "budget", "travelers",
                    "weather_summary", "hotels", "budget_breakdown",
                    "daily_itinerary", "final_report"
                }
                bad_keys = set(changes) - allowed_fields
                if bad_keys or not changes:
                    changes = None  # ignore bad update, keep the reply
                else:
                    if "destination" in changes and (
                        not isinstance(changes["destination"], str) or not changes["destination"].strip()
                    ):
                        changes = None
                    if changes and "duration_days" in changes and (
                        isinstance(changes["duration_days"], bool)
                        or not isinstance(changes["duration_days"], int)
                        or not 1 <= changes["duration_days"] <= 14
                    ):
                        changes = None
                    if changes and "budget" in changes and not _is_valid_budget(changes["budget"]):
                        changes = None
                    if changes and "travelers" in changes and (
                        isinstance(changes["travelers"], bool)
                        or not isinstance(changes["travelers"], int)
                        or changes["travelers"] < 1
                    ):
                        changes = None

        return {"reply": reply, "updated_plan": changes}

    # Fallback: treat the whole response as a plain-text reply (Gemini ignored the JSON format)
    if cleaned and len(cleaned) > 3:
        return {"reply": cleaned, "updated_plan": None}

    raise LLMInvalidResponseError(
        "Gemini returned an empty response. Please rephrase your message and try again."
    )


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


@app.get("/api/config/public")
def get_public_config():
    """Return public agency settings such as configured WhatsApp contact number."""
    return {
        "agency_name": "DreamLine Travels",
        "whatsapp_phone": settings.WHATSAPP_BUSINESS_PHONE.strip(),
        "whatsapp_configured": bool(settings.WHATSAPP_BUSINESS_PHONE.strip())
    }


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
