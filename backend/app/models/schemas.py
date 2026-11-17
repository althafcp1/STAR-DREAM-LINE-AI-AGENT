"""
Pydantic Schemas for AI Travel Planning Agent (Phase 2 & Phase 5)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    destination: str = Field(..., description="Destination city, e.g. 'Tokyo', 'Paris', 'Jaipur'")
    departure_city: Optional[str] = Field("New York", description="City of departure")
    duration_days: int = Field(3, ge=1, le=14, description="Trip duration in days (1-14)")
    budget: float = Field(1000.0, gt=0, description="Total budget in USD")
    travelers_count: int = Field(2, ge=1, le=10, description="Number of travelers")
    travel_preferences: List[str] = Field(default_factory=lambda: ["culture", "sightseeing"], description="User travel interests")
    accommodation_type: str = Field("mid", description="Hotel tier: 'budget', 'mid', or 'luxury'")
    user_id: str = Field("guest_user", description="Identifier for persistent memory recall")


class TripPlanResponse(BaseModel):
    trip_id: str
    destination: str
    duration_days: int
    budget: float
    travelers: int
    weather_summary: Dict[str, Any]
    hotels: List[Dict[str, Any]]
    budget_breakdown: Dict[str, Any]
    daily_itinerary: List[Dict[str, Any]]
    final_report: str
    team_logs: List[Dict[str, Any]]
    status: str = "success"


class ChatRequest(BaseModel):
    trip_id: Optional[str] = None
    user_id: str = "guest_user"
    destination: str = "Tokyo"
    duration_days: int = 3
    language: Optional[str] = Field("en", description="'en' for English, 'ar' for Arabic")
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User message or plan adjustment request"
    )


class ChatResponse(BaseModel):
    reply: str
    updated_plan: Optional[Dict[str, Any]] = None
    agent_thoughts: Optional[List[str]] = None
