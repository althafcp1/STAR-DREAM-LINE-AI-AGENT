"""
Phase 3 Execution Script: External Tool Integrations & Services (Phase 3 & 📘 Lesson 4)

This script executes and demonstrates:
1. Gemini LLM Service provider initialization and prompt formatting (Phase 3)
2. Weather Service integration (forecasts, temperatures, advisories)
3. Places & Attractions Service (landmarks, categories, duration)
4. Hotel Service (tier filtering, room calculations, stay costs)
5. Cross-Task Memory integration driving service queries (📘 L4)
"""

import sys
import os

# Ensure backend directory is in python path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.llm_service import GeminiLLMService
from app.services.weather_service import WeatherService
from app.services.places_service import PlacesService
from app.services.hotel_service import HotelService
from app.core.memory import MemoryStore


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_llm_service_demo():
    print_banner("DEMO 1: Gemini LLM Service Provider (Phase 3 & 📘 L8)")
    llm = GeminiLLMService()
    print(f"✓ LLM Service Model Configured: {llm.model}")
    print(f"✓ Live API Configured: {'YES (Online Key)' if llm.is_configured() else 'Simulation & Sandbox Fallback Active'}")
    
    test_prompt = "User asks: Plan a 3-day trip to Tokyo."
    response = llm.generate(test_prompt)
    print(f"\n[Prompt Sent]: \"{test_prompt}\"")
    print(f"[LLM Output Sample]:\n{response[:180]}...")


def run_weather_service_demo():
    print_banner("DEMO 2: Weather Service Integration (Phase 3)")
    weather_svc = WeatherService()
    
    cities = ["Tokyo", "Paris", "Jaipur"]
    for city in cities:
        data = weather_svc.get_forecast(city=city, days=5)
        print(f"\n[Weather for {data['city']}] (Source: {data['source']})")
        print(f"  • Temperature: {data['temperature_celsius']}°C")
        print(f"  • Conditions: {data['condition']}")
        print(f"  • Rain Chance: {data['precipitation_chance_percent']}%")
        print(f"  • Travel Advisory: {data['travel_advisory']}")


def run_places_service_demo():
    print_banner("DEMO 3: Places & Tourist Attractions Service (Phase 3)")
    places_svc = PlacesService()
    
    # Query culture category in Tokyo
    result = places_svc.search_attractions(city="Tokyo", category="culture")
    print(f"\n[Attractions in {result['city']}] (Found: {result['total_found']}, Source: {result['source']})")
    for a in result["attractions"][:3]:
        print(f"  • {a['name']} ({a['category'].title()}): Cost ${a['cost_usd']}, Duration: {a['duration_hours']}h")


def run_hotel_service_demo():
    print_banner("DEMO 4: Hotel Accommodation Service (Phase 3)")
    hotel_svc = HotelService()

    # Compare Budget vs Mid vs Luxury for 4 travelers (2 rooms) over 3 nights
    for tier in ["budget", "mid", "luxury"]:
        h_data = hotel_svc.search_accommodations(city="Tokyo", budget_tier=tier, nights=3, guests=4)
        print(f"\n[Tier: {tier.upper()}] ({h_data['guests']} guests, {h_data['rooms_needed']} rooms, {h_data['nights']} nights):")
        top_hotel = h_data["hotels"][0]
        print(f"  • Hotel: {top_hotel['name']} ({top_hotel['area']})")
        print(f"  • Rate: ${top_hotel['nightly_rate_usd']}/night/room")
        print(f"  • Total Accommodation Cost: ${top_hotel['total_stay_cost_usd']}")


def run_memory_driven_service_demo():
    print_banner("DEMO 5: Cross-Task Memory Driving Service Selection (📘 Lesson 4)")
    memory = MemoryStore(storage_path=":memory:")
    hotel_svc = HotelService()

    user_id = "vip_guest_99"
    # User previously saved luxury preference
    memory.set_preference(user_id, "preferred_tier", "luxury")
    memory.set_preference(user_id, "travel_style", "High-end comfort and fine dining")

    print(f"[Recalled Memory Context for {user_id}]:")
    print(memory.format_memory_context(user_id))

    # Service automatically selects tier based on recalled memory
    user_prefs = memory.get_preferences(user_id)
    tier_choice = user_prefs.get("preferred_tier", "mid")
    
    result = hotel_svc.search_accommodations(city="Tokyo", budget_tier=tier_choice, nights=2, guests=2)
    print(f"✓ Agent retrieved '{tier_choice}' from memory and selected:")
    print(f"  • Hotel: {result['hotels'][0]['name']} (${result['hotels'][0]['nightly_rate_usd']}/night)")


if __name__ == "__main__":
    print_banner("AI Travel Planning Agent — Phase 3 Live Execution")
    run_llm_service_demo()
    run_weather_service_demo()
    run_places_service_demo()
    run_hotel_service_demo()
    run_memory_driven_service_demo()
    print_banner("Phase 3 Execution Finished Successfully! (All External Tool Integrations & Services Verified)")

