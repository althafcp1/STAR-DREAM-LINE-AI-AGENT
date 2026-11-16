"""
FastAPI Backend Endpoints Integration Tests (Phase 5 & 8)

Tests FastAPI endpoints directly via route handler functions.
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import health_check, plan_trip, get_trip, download_trip_pdf, chat_with_agent
from app.models.schemas import TripRequest, ChatRequest


class TestAPIEndpoints(unittest.TestCase):

    def test_health_endpoint(self):
        """Verify health_check() returns operational status."""
        data = health_check()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["tools_loaded"], 4)
        self.assertEqual(data["agents_active"], 6)

    def test_trip_plan_and_pdf_flow(self):
        """Verify complete trip planning lifecycle: Plan -> Retrieve -> Download PDF."""
        req = TripRequest(
            destination="Tokyo",
            departure_city="San Francisco",
            duration_days=3,
            budget=1200.0,
            travelers_count=2,
            travel_preferences=["culture", "sightseeing"],
            accommodation_type="mid",
            user_id="test_api_traveler"
        )

        # 1. Plan Trip
        plan_data = plan_trip(req)
        self.assertIn("trip_id", plan_data)
        self.assertEqual(plan_data["destination"], "Tokyo")
        self.assertEqual(len(plan_data["daily_itinerary"]), 3)
        self.assertGreater(len(plan_data["hotels"]), 0)
        self.assertGreater(len(plan_data["team_logs"]), 0)

        trip_id = plan_data["trip_id"]

        # 2. Retrieve Stored Trip
        saved_plan = get_trip(trip_id)
        self.assertEqual(saved_plan["destination"], "Tokyo")

        # 3. Generate Downloadable PDF
        pdf_response = download_trip_pdf(trip_id)
        self.assertEqual(pdf_response.media_type, "application/pdf")
        self.assertTrue(pdf_response.body.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_response.body), 2000)

    def test_chat_modification_endpoint(self):
        """Verify chat_with_agent() provides contextual travel advice."""
        chat_req = ChatRequest(
            destination="Paris",
            duration_days=4,
            message="Can you recommend cheaper accommodation options?"
        )
        with patch(
            "app.main.llm_service.generate",
            return_value='{"reply":"For a lower-cost stay, compare hostels and guesthouses.",'
                         '"updated_plan":null}'
        ) as generate:
            chat_resp = chat_with_agent(chat_req)

        generate.assert_called_once()
        self.assertFalse(generate.call_args.kwargs["allow_offline_fallback"])
        self.assertIsNotNone(chat_resp.reply)
        self.assertIn("lower-cost", chat_resp.reply.lower())


if __name__ == "__main__":
    unittest.main()
