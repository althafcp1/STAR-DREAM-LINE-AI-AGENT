"""
Specialized Worker Agents (⭐ Bonus: Lesson 6: A Team of Agents)

Each agent focuses on a single domain of expertise and collaborates via TeamState.
"""

from typing import Dict, Any, List
from app.core.tools import (
    search_destinations_and_attractions,
    get_weather_forecast,
    search_hotels,
    calculate_budget_allocation
)
from app.multi_agent.state import TeamState


class DestinationAgent:
    """Specialist in tourist sights, cultural landmarks, and local activities."""
    ROLE = "Destination Research Agent"

    def execute(self, state: TeamState) -> None:
        state.log_activity(self.ROLE, f"Researching top cultural and sightseeing locations in {state.destination}...")
        try:
            result = search_destinations_and_attractions(city=state.destination, category="all")
            state.destination_data = result
            state.log_activity(self.ROLE, f"Identified {result['total_attractions_found']} top attractions.")
        except Exception as e:
            state.log_activity(self.ROLE, f"Encountered error researching destination: {e}")


class WeatherAgent:
    """Specialist in meteorological forecasts and packing advisories."""
    ROLE = "Weather Forecast Agent"

    def execute(self, state: TeamState) -> None:
        state.log_activity(self.ROLE, f"Retrieving weather forecast for {state.destination}...")
        try:
            result = get_weather_forecast(city=state.destination, days=min(state.duration_days, 14))
            state.weather_data = result
            state.log_activity(
                self.ROLE,
                f"Conditions: {result['condition']}, Avg Temp: {result['temperature_celsius']}°C. Advisory: {result['travel_advisory']}"
            )
        except Exception as e:
            state.log_activity(self.ROLE, f"Weather retrieval note: {e}")


class HotelAgent:
    """Specialist in accommodations and lodging matching the traveler's budget."""
    ROLE = "Hotel Accommodation Agent"

    def execute(self, state: TeamState) -> None:
        state.log_activity(self.ROLE, f"Searching hotels in {state.destination} for {state.travelers} guests...")
        tier = "budget" if state.budget < 600 else ("luxury" if state.budget > 2500 else "mid")
        try:
            result = search_hotels(
                city=state.destination,
                budget_tier=tier,
                nights=max(1, state.duration_days - 1),
                guests=state.travelers
            )
            state.hotel_data = result
            top_hotel = result["hotels"][0] if result.get("hotels") else None
            if top_hotel:
                state.log_activity(self.ROLE, f"Recommended: {top_hotel['name']} (${top_hotel['nightly_rate_usd']}/night).")
        except Exception as e:
            state.log_activity(self.ROLE, f"Hotel search error: {e}")


class BudgetAgent:
    """Specialist in financial calculations, cost breakdowns, and emergency buffers."""
    ROLE = "Budget Planning Agent"

    def execute(self, state: TeamState) -> None:
        state.log_activity(self.ROLE, f"Calculating comprehensive budget breakdown for ${state.budget}...")
        stay_cost = 0.0
        if state.hotel_data and state.hotel_data.get("hotels"):
            stay_cost = state.hotel_data["hotels"][0]["total_stay_cost_usd"]

        activities_cost = 0.0
        if state.destination_data and state.destination_data.get("attractions"):
            activities_cost = sum(a.get("cost_usd", 0) for a in state.destination_data["attractions"][:state.duration_days * 2])

        try:
            result = calculate_budget_allocation(
                total_budget=state.budget,
                stay_cost=stay_cost,
                activities_cost=activities_cost,
                days=state.duration_days,
                guests=state.travelers
            )
            state.budget_breakdown = result
            state.log_activity(
                self.ROLE,
                f"Budget healthy! Allocated: Food ${result['estimated_food_total_usd']}, Transit ${result['estimated_local_transit_usd']}, Buffer ${result['emergency_buffer_usd']}."
            )
        except Exception as e:
            state.log_activity(self.ROLE, f"Budget alert: {e}")


class ItineraryAgent:
    """Specialist in sequencing attractions into morning, afternoon, and evening slots."""
    ROLE = "Itinerary Scheduling Agent"

    def execute(self, state: TeamState) -> None:
        state.log_activity(self.ROLE, f"Constructing {state.duration_days}-day itinerary...")
        attractions = state.destination_data.get("attractions", []) if state.destination_data else []
        
        schedule: List[Dict[str, Any]] = []
        attraction_idx = 0
        
        for day in range(1, state.duration_days + 1):
            day_plan = {
                "day": day,
                "title": f"Day {day}: Exploring {state.destination}",
                "slots": {
                    "morning": attractions[attraction_idx % len(attractions)]["name"] if attractions else "Explore local morning market",
                    "afternoon": attractions[(attraction_idx + 1) % len(attractions)]["name"] if attractions else "Local museum & dining",
                    "evening": "Sunset stroll and authentic local cuisine dinner"
                }
            }
            attraction_idx += 2
            schedule.append(day_plan)

        state.daily_schedule = schedule
        state.log_activity(self.ROLE, f"Daily itinerary completed for {state.duration_days} days.")

