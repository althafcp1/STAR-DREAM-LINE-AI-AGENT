"""
Unit Test for PDF Report Generation (Phase 6)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.pdf_service import TravelPDFGenerator


class TestPDFGeneration(unittest.TestCase):

    def test_pdf_generation_bytes(self):
        generator = TravelPDFGenerator()
        sample_plan = {
            "destination": "Tokyo",
            "duration_days": 3,
            "budget": 1200.0,
            "travelers": 2,
            "weather_data": {
                "avg_temp_c": 19,
                "temperature_celsius": 19,
                "condition": "Clear Skies",
                "travel_advisory": "Pleasant weather for walking tours."
            },
            "hotel_data": {
                "hotels": [
                    {
                        "name": "Hotel Gracery Shinjuku",
                        "area": "Shinjuku",
                        "rating": 4.5,
                        "nightly_rate_usd": 130.0,
                        "total_stay_cost_usd": 260.0
                    }
                ]
            },
            "budget_breakdown": {
                "stay_cost_usd": 260.0,
                "estimated_food_total_usd": 400.0,
                "daily_food_per_person_usd": 66.6,
                "estimated_local_transit_usd": 150.0,
                "daily_transit_usd": 50.0,
                "activities_cost_usd": 60.0,
                "emergency_buffer_usd": 150.0
            },
            "daily_schedule": [
                {
                    "day": 1,
                    "title": "Day 1: Historic Tokyo",
                    "slots": {
                        "morning": "Senso-ji Temple",
                        "afternoon": "Akihabara Tech District",
                        "evening": "Shinjuku Nightwalk & Ramen"
                    }
                }
            ]
        }

        pdf_bytes = generator.generate_pdf(sample_plan)
        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        # Verify PDF header magic bytes "%PDF-"
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        print(f"\n[PDF Test Success] Generated {len(pdf_bytes)} bytes of valid PDF document.")


if __name__ == "__main__":
    unittest.main()

