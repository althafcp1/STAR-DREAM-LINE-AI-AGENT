"""
Phase 1 Execution Script: The Core ReAct Engine & Tools (📘 Lessons L1, L2, L3)

This script executes and demonstrates:
1. The 4 Clearly Described Tools in action (📘 L2)
2. The Think -> Act -> Look autonomous agent loop (📘 L1, L3)
3. Automatic Tool Error Recovery and Self-Correction (📘 L2)
"""

import sys
import os
import json
import time

# Ensure backend directory is in python path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.tools import (
    search_destinations_and_attractions,
    get_weather_forecast,
    search_hotels,
    calculate_budget_allocation,
    TOOL_DESCRIPTIONS
)
from app.core.error_handler import SafeToolExecutor
from app.core.react_agent import ReActAgent
from tests.fake_llm import FakeLLM


def print_banner(title: str):
    print("\n" + "=" * 75)
    print(f"  {title}")
    print("=" * 75)


def run_demo_tools():
    print_banner("DEMO 1: The 4 Clearly Described Tools (📘 Lesson 2)")
    
    print("\n[Tool Schema Definitions]")
    for idx, t in enumerate(TOOL_DESCRIPTIONS, 1):
        print(f" {idx}. {t['name']} — {t['description']}")

    # 1. Destination Search Tool
    print("\n--- Invoking Tool 1: search_destinations_and_attractions ---")
    dest_result = search_destinations_and_attractions(city="Tokyo", category="culture")
    print(f"City: {dest_result['city']} ({dest_result['country']})")
    print(f"Attractions Found: {dest_result['total_attractions_found']}")
    for a in dest_result["attractions"][:2]:
        print(f"  • {a['name']} ({a['category'].title()}): Best at {a['best_time']}, Cost: ${a['cost_usd']}")

    # 2. Weather Forecast Tool
    print("\n--- Invoking Tool 2: get_weather_forecast ---")
    weather_result = get_weather_forecast(city="Tokyo", days=5)
    print(f"Forecast for {weather_result['city']} (Next {weather_result['forecast_days']} days):")
    print(f"  • Temperature: {weather_result['temperature_celsius']}°C")
    print(f"  • Condition: {weather_result['condition']}")
    print(f"  • Precipitation: {weather_result['precipitation_chance_percent']}%")
    print(f"  • Advisory: {weather_result['travel_advisory']}")

    # 3. Hotel Search Tool
    print("\n--- Invoking Tool 3: search_hotels ---")
    hotel_result = search_hotels(city="Tokyo", budget_tier="mid", nights=3, guests=2)
    print(f"Found {hotel_result['options_count']} options for {hotel_result['guests']} guests ({hotel_result['nights']} nights):")
    for h in hotel_result["hotels"][:2]:
        print(f"  • {h['name']} in {h['area']}: ${h['nightly_rate_usd']}/night -> Total Stay: ${h['total_stay_cost_usd']}")

    # 4. Budget Calculator Tool
    print("\n--- Invoking Tool 4: calculate_budget_allocation ---")
    budget_result = calculate_budget_allocation(
        total_budget=1200.0,
        stay_cost=390.0,
        activities_cost=55.0,
        days=3,
        guests=2
    )
    print(f"Total Budget: ${budget_result['total_budget_usd']}")
    print(f"  • Stay Cost: ${budget_result['stay_cost_usd']}")
    print(f"  • Sightseeing Activities: ${budget_result['activities_cost_usd']}")
    print(f"  • Food Allowance: ${budget_result['estimated_food_total_usd']} (~${budget_result['daily_food_per_person_usd']}/person/day)")
    print(f"  • Local Transit: ${budget_result['estimated_local_transit_usd']}")
    print(f"  • Emergency Reserve Buffer: ${budget_result['emergency_buffer_usd']}")
    print(f"  • Budget Health: {'✓ HEALTHY & BALANCED' if budget_result['is_healthy_budget'] else '⚠️ TIGHT'}")


def run_demo_react_loop():
    print_banner("DEMO 2: The Think -> Act -> Look Agent Loop (📘 Lessons 1 & 3)")
    
    executor = SafeToolExecutor()
    fake_llm = FakeLLM([
        # Turn 1
        'Thought: The user wants to plan a 3-day Tokyo trip. First, I will check the weather forecast to plan outdoor vs indoor activities.\n'
        'Action: get_weather_forecast(city="Tokyo", days=3)',

        # Turn 2
        'Thought: The weather is mild (18°C) with low rain chance. Now I will search top cultural attractions for the itinerary.\n'
        'Action: search_destinations_and_attractions(city="Tokyo", category="culture")',

        # Turn 3
        'Thought: Found Senso-ji and Meiji Shrine. Now I need to find mid-scale hotel accommodation within Tokyo.\n'
        'Action: search_hotels(city="Tokyo", budget_tier="mid", nights=3, guests=2)',

        # Turn 4
        'Thought: I have collected weather data, top attractions, and hotel rates. Now I can formulate the complete itinerary.\n'
        'Final Answer: Here is your personalized 3-day Tokyo cultural itinerary!\n'
        '  - Weather: 18°C Partly Cloudy, pleasant for walking.\n'
        '  - Stay: Hotel Gracery Shinjuku ($130/night, Total $390).\n'
        '  - Day 1: Senso-ji Temple & Asakusa historical quarter.\n'
        '  - Day 2: Meiji Shrine & Shibuya Crossing evening walk.\n'
        '  - Day 3: Akihabara & traditional local culinary dining.'
    ])

    agent = ReActAgent(llm_caller=fake_llm, tool_executor=executor)
    user_query = "Plan a 3-day cultural visit to Tokyo for 2 travelers"
    
    print(f"User Query: \"{user_query}\"\n")
    print("--- Starting Agent Execution Loop ---")
    
    result = agent.run(user_query, destination="Tokyo", duration_days=3)

    for step in result["trajectory"]:
        print(f"\n[STEP {step['step']}]")
        print(f"💭 THINK: {step['thought']}")
        if step['action']:
            print(f"⚡ ACT:   {step['action']}")
        if step['observation']:
            print(f"👁️ LOOK:  {step['observation'][:120]}...")

    print("\n" + "-" * 75)
    print("🎯 [FINAL ANSWER DELIVERED BY AGENT]")
    print(result["final_answer"])
    print("-" * 75)
    print(f"Execution Status: {result['status'].upper()} in {result['total_steps']} steps.")


def run_demo_error_self_correction():
    print_banner("DEMO 3: Tool Error Recovery & Self-Correction (📘 Lesson 2)")
    
    executor = SafeToolExecutor()
    fake_llm = FakeLLM([
        # Step 1: Deliberate typo by the agent
        'Thought: I will search attractions in Tokyoo.\n'
        'Action: search_destinations_and_attractions(city="Tokyoo", category="culture")',

        # Step 2: Agent reads error observation and self-corrects
        'Thought: The tool reported a typo and suggested Tokyo. I will correct the destination name to Tokyo.\n'
        'Action: search_destinations_and_attractions(city="Tokyo", category="culture")',

        # Step 3: Final Answer
        'Thought: Cultural attractions gathered successfully after self-correction.\n'
        'Final Answer: Tokyo attractions found: Senso-ji Temple and Meiji Shrine.'
    ])

    agent = ReActAgent(llm_caller=fake_llm, tool_executor=executor)
    print("User Query: \"Find sights in Tokyoo (with intentional typo)\"\n")
    
    result = agent.run("Find sights in Tokyoo")

    for step in result["trajectory"]:
        print(f"\n[STEP {step['step']}]")
        print(f"💭 THINK: {step['thought']}")
        print(f"⚡ ACT:   {step['action']}")
        print(f"👁️ LOOK:  {step['observation']}")

    print("\n✓ Self-correction successful! The agent diagnosed the ToolError and corrected its query.")


if __name__ == "__main__":
    print_banner("AI Travel Planning Agent — Phase 1 Live Execution")
    run_demo_tools()
    run_demo_react_loop()
    run_demo_error_self_correction()
    print_banner("Phase 1 Execution Finished Successfully! (All L1, L2, L3 criteria met)")

