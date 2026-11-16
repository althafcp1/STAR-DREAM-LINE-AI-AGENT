"""
Phase 2 Execution Script: Database Setup & Data Schemas (Phase 2 & 📘 Lesson 4)

This script executes and demonstrates:
1. Pydantic schema validation (TripRequest, BudgetBreakdown, TripPlanResponse)
2. Database schema initialization (Trips, UserMemory, AuditLogs)
3. Storing and retrieving trip plans with full JSON deserialization
4. Cross-task memory read/write persistence (📘 L4)
5. Structured audit log persistence (📘 L7)
"""

import sys
import os
import json
import uuid

# Ensure backend directory is in python path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.models.schemas import TripRequest, TripPlanResponse
from app.models.database import DatabaseManager


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_schema_validation_demo():
    print_banner("DEMO 1: Pydantic Data Schema Validation (Phase 2)")

    # 1. Valid Request
    print("\n[Validating Proper TripRequest]")
    valid_payload = {
        "destination": "Kyoto",
        "departure_city": "Tokyo",
        "duration_days": 4,
        "budget": 1500.0,
        "travelers_count": 2,
        "travel_preferences": ["culture", "tea_ceremony", "gardens"],
        "accommodation_type": "mid",
        "user_id": "traveler_42"
    }
    req = TripRequest(**valid_payload)
    print(f"✓ Valid TripRequest parsed successfully for: {req.destination}")
    print(f"  Duration: {req.duration_days} days | Budget: ${req.budget} | Travelers: {req.travelers_count}")

    # 2. Schema Enforcement: Out of range duration
    print("\n[Testing Validation Guardrails: Duration > 14 days]")
    try:
        invalid_payload = valid_payload.copy()
        invalid_payload["duration_days"] = 30  # Exceeds max 14 days
        TripRequest(**invalid_payload)
        print("❌ Failed: Should have rejected duration > 14")
    except Exception as e:
        print(f"✓ Pydantic rejected invalid duration: {e.errors()[0]['msg']}")

    # 3. Schema Enforcement: Negative budget
    print("\n[Testing Validation Guardrails: Budget <= 0]")
    try:
        invalid_payload = valid_payload.copy()
        invalid_payload["budget"] = -250.0  # Invalid budget
        TripRequest(**invalid_payload)
        print("❌ Failed: Should have rejected negative budget")
    except Exception as e:
        print(f"✓ Pydantic rejected negative budget: {e.errors()[0]['msg']}")


def run_database_persistence_demo():
    print_banner("DEMO 2: Database Initialization & Trip Persistence (Phase 2)")

    db_file = "test_phase2_travel.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    db = DatabaseManager(db_path=db_file)
    print(f"✓ SQLite Database initialized with schema at: {db_file}")

    trip_id = str(uuid.uuid4())
    user_id = "traveler_42"

    sample_plan = {
        "destination": "Kyoto",
        "departure_city": "Tokyo",
        "duration_days": 4,
        "budget": 1500.0,
        "travelers": 2,
        "weather_summary": {
            "temperature_celsius": 17,
            "condition": "Clear & Sunny",
            "travel_advisory": "Pleasant walking conditions."
        },
        "hotels": [
            {
                "name": "Kyoto Century Hotel",
                "area": "Shimogyo Ward",
                "rating": 4.6,
                "nightly_rate_usd": 140.0,
                "total_stay_cost_usd": 560.0,
                "amenities": ["WiFi", "Breakfast", "Garden View"]
            }
        ],
        "budget_breakdown": {
            "stay_cost_usd": 560.0,
            "activities_cost_usd": 120.0,
            "estimated_food_total_usd": 450.0,
            "estimated_local_transit_usd": 180.0,
            "emergency_buffer_usd": 190.0,
            "total_allocated_usd": 1500.0,
            "is_healthy_budget": True
        },
        "daily_itinerary": [
            {
                "day": 1,
                "title": "Day 1: Historic Temples",
                "slots": {
                    "morning": "Fushimi Inari Taisha (Torii Gates)",
                    "afternoon": "Kiyomizu-dera Temple & Ninenzaka",
                    "evening": "Gion district evening culinary tour"
                }
            },
            {
                "day": 2,
                "title": "Day 2: Bamboo Groves & Castles",
                "slots": {
                    "morning": "Arashiyama Bamboo Grove & Tenryu-ji",
                    "afternoon": "Kinkaku-ji (Golden Pavilion)",
                    "evening": "Pontocho Alley dinner"
                }
            }
        ],
        "final_report": "Personalized Kyoto 4-day cultural journey complete."
    }

    # 1. Save trip
    print(f"\n[Saving Trip Plan: ID={trip_id}]")
    db.save_trip(trip_id, user_id, sample_plan)
    print(f"✓ Trip '{sample_plan['destination']}' saved successfully.")

    # 2. Retrieve trip
    print(f"\n[Querying Database for Trip ID: {trip_id}]")
    retrieved = db.get_trip(trip_id)
    assert retrieved is not None
    print(f"✓ Successfully retrieved trip from DB:")
    print(f"  • Destination: {retrieved['destination']}")
    print(f"  • Budget: ${retrieved['budget']:,.2f}")
    print(f"  • Hotels Loaded: {len(retrieved['hotels'])} ({retrieved['hotels'][0]['name']})")
    print(f"  • Itinerary Days Loaded: {len(retrieved['daily_itinerary'])}")
    print(f"  • Food Allowance: ${retrieved['budget_breakdown']['estimated_food_total_usd']}")

    # 3. User Memory Persistence (📘 L4)
    print_banner("DEMO 3: Cross-Task Persistent Memory in Database (📘 Lesson 4)")
    print(f"[Recording User Preferences for user '{user_id}']")
    db.set_user_memory(user_id, "dietary", "Pescatarian")
    db.set_user_memory(user_id, "pace", "Relaxed & cultural")
    db.set_user_memory(user_id, "interests", ["heritage", "traditional tea", "gardens"])

    print("✓ Preferences written to database.")
    
    print("\n[Simulating New Task / Session: Retrieving Stored Memory]")
    memories = db.get_user_memories(user_id)
    for k, v in memories.items():
        print(f"  • {k.title()}: {v}")

    # 4. Audit Log (📘 L7)
    print_banner("DEMO 4: Structured Audit Logging to Database (📘 Lesson 7)")
    db.log_audit(trip_id, "safety_check_passed", {"threshold": 500.0, "status": "approved"})
    db.log_audit(trip_id, "plan_generated", {"agent": "Supervisor", "steps": 5})

    counts = db.count_records()
    print("✓ Database Records Summary:")
    print(f"  • Saved Trips: {counts['trips_count']}")
    print(f"  • User Memory Traits: {counts['user_memory_count']}")
    print(f"  • Audit Log Entries: {counts['audit_logs_count']}")

    # Cleanup test db
    del db
    import gc
    gc.collect()
    try:
        if os.path.exists(db_file):
            os.remove(db_file)
        print("✓ Cleaned up test database.")
    except Exception:
        print("✓ Database operations complete.")


if __name__ == "__main__":
    print_banner("AI Travel Planning Agent — Phase 2 Live Execution")
    run_schema_validation_demo()
    run_database_persistence_demo()
    print_banner("Phase 2 Execution Finished Successfully! (All Data Schemas & Database Operations Verified)")
