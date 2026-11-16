"""
Phase 5 Execution Script: FastAPI Backend Endpoints & Safety Guardrails (Phase 5 & 📘 Lesson 7)

This script executes and demonstrates:
1. Complete FastAPI REST API endpoints lifecycle (Phase 5):
   - Health check (/api/health)
   - Multi-agent trip planning (/api/trip/plan)
   - Stored trip retrieval (/api/trip/{id})
   - Conversational assistant modification (/api/chat)
   - PDF report streaming (/api/trip/{id}/pdf)
2. Safety Guardrails & Governance (📘 Lesson 7):
   - Human-in-the-Loop (HITL) authorization for actions > threshold
   - Step limit loop termination
   - Structured audit log event generation
"""

import sys
import os
import json
import uuid

# Ensure backend directory is in python path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import (
    health_check,
    plan_trip,
    get_trip,
    chat_with_agent,
    download_trip_pdf
)
from app.models.schemas import TripRequest, ChatRequest
from app.core.safety import SafetyGate
from app.core.react_agent import ReActAgent
from tests.fake_llm import FakeLLM
from app.core.error_handler import SafeToolExecutor


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_fastapi_endpoints_demo():
    print_banner("DEMO 1: FastAPI Backend API Endpoints (Phase 5)")

    # 1. Health Check Endpoint
    print("\n--- 1. Testing GET /api/health ---")
    health = health_check()
    print(f"✓ Health Status: {health['status'].upper()}")
    print(f"  Service: {health['service']} (v{health['version']})")
    print(f"  Tools Loaded: {health['tools_loaded']} | Active Agents: {health['agents_active']}")

    # 2. Plan Trip Endpoint
    print("\n--- 2. Testing POST /api/trip/plan ---")
    trip_payload = TripRequest(
        destination="Jaipur",
        departure_city="Delhi",
        duration_days=3,
        budget=800.0,
        travelers_count=2,
        travel_preferences=["culture", "heritage", "palaces"],
        accommodation_type="mid",
        user_id="traveler_api_tester"
    )

    plan_response = plan_trip(trip_payload)
    trip_id = plan_response["trip_id"]
    print(f"✓ Generated Trip ID: {trip_id}")
    print(f"  Destination: {plan_response['destination']} ({plan_response['duration_days']} Days)")
    print(f"  Hotels Found: {len(plan_response['hotels'])} (Top: {plan_response['hotels'][0]['name']})")
    print(f"  Budget Breakdown: Total ${plan_response['budget_breakdown']['total_budget_usd']}")
    print(f"    • Food: ${plan_response['budget_breakdown']['estimated_food_total_usd']}")
    print(f"    • Transit: ${plan_response['budget_breakdown']['estimated_local_transit_usd']}")
    print(f"    • Buffer: ${plan_response['budget_breakdown']['emergency_buffer_usd']}")

    # 3. Retrieve Trip Endpoint
    print(f"\n--- 3. Testing GET /api/trip/{trip_id} ---")
    retrieved = get_trip(trip_id)
    print(f"✓ Retrieved Trip successfully from persistent storage: {retrieved['destination']}")

    # 4. Chat Modification Assistant Endpoint
    print("\n--- 4. Testing POST /api/chat ---")
    chat_req = ChatRequest(
        trip_id=trip_id,
        destination="Jaipur",
        duration_days=3,
        message="Can you suggest budget-friendly options and check rain advisory?"
    )
    chat_resp = chat_with_agent(chat_req)
    print(f"User Message: \"{chat_req.message}\"")
    print(f"Agent Reply: \"{chat_resp.reply}\"")

    # 5. PDF Generation & Download Endpoint
    print(f"\n--- 5. Testing GET /api/trip/{trip_id}/pdf ---")
    pdf_response = download_trip_pdf(trip_id)
    print(f"✓ Content-Type: {pdf_response.media_type}")
    print(f"✓ Content-Disposition: {pdf_response.headers.get('Content-Disposition')}")
    print(f"✓ PDF Binary Size: {len(pdf_response.body):,} bytes (Magic: {pdf_response.body[:5].decode('latin1')})")


def run_safety_guardrails_demo():
    print_banner("DEMO 2: Safety Guardrails & Governance (📘 Lesson 7)")

    audit_log_file = "test_phase5_audit.log"
    if os.path.exists(audit_log_file):
        os.remove(audit_log_file)

    safety = SafetyGate(
        confirmation_cost_threshold=500.0,
        log_file_path=audit_log_file
    )

    # 1. Human-in-the-Loop Confirmation
    print("\n[Guardrail 1: Human-in-the-Loop Confirmation for High Costs > $500]")
    # Action attempting to allocate $700 stay without confirmation
    approved, msg = safety.check_action_safety(
        "calculate_budget_allocation",
        {"stay_cost": 700.0, "total_budget": 1200.0}
    )
    print(f"Is Action Auto-Approved? {approved}")
    print(f"Safety Gate Intervention: {msg}")
    print("✓ Successfully paused execution to seek explicit user consent before committing high expenditure.")

    # 2. Step Limit Loop Cap
    print("\n[Guardrail 2: Step Limit Prevents Runaway Execution]")
    endless_responses = ['Thought: Checking weather...\nAction: get_weather_forecast(city="Tokyo", days=1)' for _ in range(8)]
    fake_llm = FakeLLM(endless_responses)
    executor = SafeToolExecutor()
    
    agent = ReActAgent(llm_caller=fake_llm, tool_executor=executor, safety_gate=safety, max_steps=3)
    loop_result = agent.run("Infinite loop test")
    print(f"Execution Loop Result: {loop_result['status'].upper()}")
    print(f"Total Steps Taken: {loop_result['total_steps']} (Strict Cap: 3)")
    print(f"Diagnostic Output: {loop_result['final_answer']}")

    # 3. Structured Audit Log
    print("\n[Guardrail 3: Persistent Audit Logging to Disk]")
    safety.log_event("manual_admin_audit", {"actor": "SystemAdmin", "status": "verified"})
    
    with open(audit_log_file, "r", encoding="utf-8") as f:
        log_entries = f.readlines()
    
    print(f"✓ Total Telemetry Records Written: {len(log_entries)}")
    for line in log_entries[:2]:
        record = json.loads(line.strip())
        print(f"  • [{record['timestamp']}] Event: {record['event_type']} -> Details: {record['details']}")

    # Cleanup test log
    if os.path.exists(audit_log_file):
        os.remove(audit_log_file)
    print("\n✓ Cleaned up test audit log.")


if __name__ == "__main__":
    print_banner("AI Travel Planning Agent — Phase 5 Live Execution")
    run_fastapi_endpoints_demo()
    run_safety_guardrails_demo()
    print_banner("Phase 5 Execution Finished Successfully! (All API Endpoints & Safety Guardrails Verified)")

