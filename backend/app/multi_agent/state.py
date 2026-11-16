"""
Shared Multi-Agent Team State (⭐ Bonus: Lesson 6: A Team of Agents)

Defines the shared state dictionary exchanged between the Supervisor and Worker Agents.
"""

from typing import Dict, Any, List, Optional


class TeamState:
    """
    Encapsulates the evolving collective intelligence of the agent team.
    """
    def __init__(self, user_query: str, destination: str, duration_days: int = 3, budget: float = 1000.0, travelers: int = 2):
        self.user_query = user_query
        self.destination = destination
        self.duration_days = duration_days
        self.budget = budget
        self.travelers = travelers
        
        # Agent contributions
        self.destination_data: Optional[Dict[str, Any]] = None
        self.weather_data: Optional[Dict[str, Any]] = None
        self.hotel_data: Optional[Dict[str, Any]] = None
        self.budget_breakdown: Optional[Dict[str, Any]] = None
        self.daily_schedule: Optional[List[Dict[str, Any]]] = None
        self.final_report: Optional[str] = None
        
        # Team interaction log
        self.activity_log: List[Dict[str, Any]] = []

    def log_activity(self, agent_role: str, message: str) -> None:
        self.activity_log.append({
            "agent": agent_role,
            "message": message
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.user_query,
            "destination": self.destination,
            "duration_days": self.duration_days,
            "budget": self.budget,
            "travelers": self.travelers,
            "destination_data": self.destination_data,
            "weather_data": self.weather_data,
            "hotel_data": self.hotel_data,
            "budget_breakdown": self.budget_breakdown,
            "daily_schedule": self.daily_schedule,
            "final_report": self.final_report,
            "team_logs": self.activity_log
        }

