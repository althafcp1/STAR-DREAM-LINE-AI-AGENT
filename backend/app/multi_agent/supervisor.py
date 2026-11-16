"""
Travel Manager Supervisor (⭐ Bonus: Lesson 6: A Team of Agents)

Central orchestrator that coordinates specialized worker agents:
1. Decomposes the user's travel mission.
2. Dispatches sub-tasks to Destination, Weather, Hotel, Budget, and Itinerary agents.
3. Synthesizes collective findings into a unified, publication-ready travel plan.
"""

from typing import Dict, Any
from app.multi_agent.state import TeamState
from app.multi_agent.worker_agents import (
    DestinationAgent,
    WeatherAgent,
    HotelAgent,
    BudgetAgent,
    ItineraryAgent
)


class TravelManagerSupervisor:
    """
    Supervisor Agent coordinating the multi-agent travel team (📘 L6).
    """
    ROLE = "Travel Manager Supervisor"

    def __init__(self):
        self.destination_agent = DestinationAgent()
        self.weather_agent = WeatherAgent()
        self.hotel_agent = HotelAgent()
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent()

    def plan_trip(
        self,
        query: str,
        destination: str,
        duration_days: int = 3,
        budget: float = 1200.0,
        travelers: int = 2
    ) -> Dict[str, Any]:
        """
        Coordinates the complete multi-agent workflow.
        """
        state = TeamState(
            user_query=query,
            destination=destination,
            duration_days=duration_days,
            budget=budget,
            travelers=travelers
        )

        state.log_activity(self.ROLE, f"Initiating coordinated multi-agent mission for {destination} ({duration_days} days).")

        # Step 1: Research destination attractions & weather in parallel/sequence
        self.destination_agent.execute(state)
        self.weather_agent.execute(state)

        # Step 2: Search accommodations matching budget tier
        self.hotel_agent.execute(state)

        # Step 3: Run comprehensive budget calculations
        self.budget_agent.execute(state)

        # Step 4: Construct optimized daily itinerary
        self.itinerary_agent.execute(state)

        # Step 5: Supervisor synthesizes the final comprehensive package
        state.final_report = self._synthesize_final_report(state)
        state.log_activity(self.ROLE, "All agent tasks validated and final travel plan synthesized.")

        return state.to_dict()

    def _synthesize_final_report(self, state: TeamState) -> str:
        hotel_name = "Recommended lodging"
        if state.hotel_data and state.hotel_data.get("hotels"):
            hotel_name = state.hotel_data["hotels"][0]["name"]

        weather_cond = state.weather_data.get("condition", "Mild") if state.weather_data else "Mild"
        temp = state.weather_data.get("temperature_celsius", 20) if state.weather_data else 20
        buffer_amount = state.budget_breakdown.get("emergency_buffer_usd", 0) if state.budget_breakdown else 0

        report = [
            f"# Personalized Travel Plan: {state.destination} ({state.duration_days} Days)",
            f"**Travelers:** {state.travelers} | **Total Budget:** ${state.budget:.2f}",
            "",
            "## 🌤️ Weather Overview",
            f"- **Forecast:** {weather_cond}, ~{temp}°C",
            f"- **Advisory:** {state.weather_data.get('travel_advisory', 'Enjoy your trip!') if state.weather_data else 'Safe travels!'}",
            "",
            "## 🏨 Recommended Accommodation",
            f"- **Hotel:** {hotel_name}",
            f"- **Stay Cost:** ${state.budget_breakdown.get('stay_cost_usd', 0):.2f}" if state.budget_breakdown else "",
            "",
            "## 💰 Financial Breakdown",
            f"- **Food & Dining:** ${state.budget_breakdown.get('estimated_food_total_usd', 0):.2f}" if state.budget_breakdown else "",
            f"- **Local Transit:** ${state.budget_breakdown.get('estimated_local_transit_usd', 0):.2f}" if state.budget_breakdown else "",
            f"- **Emergency Buffer:** ${buffer_amount:.2f}",
            "",
            "## 📅 Daily Itinerary"
        ]

        if state.daily_schedule:
            for day in state.daily_schedule:
                report.append(f"### {day['title']}")
                report.append(f"- **Morning:** {day['slots']['morning']}")
                report.append(f"- **Afternoon:** {day['slots']['afternoon']}")
                report.append(f"- **Evening:** {day['slots']['evening']}")

        return "\n".join(report)

