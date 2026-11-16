import json
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app import main
from app.models.database import DatabaseManager
from app.models.schemas import ChatRequest
from app.services.llm_service import (
    GeminiLLMService,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError
)


class TestChatIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_manager = main.db_manager
        self.original_trip_storage = main.TRIP_STORAGE
        self.original_trip_owners = main.TRIP_OWNERS
        main.db_manager = DatabaseManager(os.path.join(self.temp_dir.name, "chat-test.db"))
        main.TRIP_STORAGE = {}
        main.TRIP_OWNERS = {}

    def tearDown(self):
        main.db_manager = self.original_db_manager
        main.TRIP_STORAGE = self.original_trip_storage
        main.TRIP_OWNERS = self.original_trip_owners
        self.temp_dir.cleanup()

    def _create_trip(self):
        plan = {
            "trip_id": "chat-trip",
            "destination": "Tokyo",
            "duration_days": 3,
            "budget": 1200.0,
            "travelers": 2,
            "weather_summary": {"condition": "Clear"},
            "hotels": [{"name": "Tokyo Central Hotel", "nightly_rate_usd": 120}],
            "budget_breakdown": {"stay_cost_usd": 360, "total_budget_usd": 1200},
            "daily_itinerary": [{
                "day": 1,
                "title": "Day 1: Tokyo",
                "slots": {
                    "morning": "Senso-ji",
                    "afternoon": "Ueno Park",
                    "evening": "Dinner in Asakusa"
                }
            }],
            "final_report": "Tokyo trip plan"
        }
        main.TRIP_STORAGE[plan["trip_id"]] = dict(plan)
        main.TRIP_OWNERS[plan["trip_id"]] = "chat-test-user"
        main.db_manager.save_trip(plan["trip_id"], "chat-test-user", plan)
        return plan

    def test_requested_conversation_scenarios_use_gemini_and_memory(self):
        self._create_trip()
        scenarios = [
            ("Hi", "Hello! Welcome to Dream Line Travels."),
            ("What can you do?", "I can help with destinations and itineraries."),
            ("Tell me about Tokyo", "Tokyo blends historic temples and modern neighborhoods."),
            ("Suggest cheaper hotels", "Consider a hostel or budget guesthouse."),
            ("Make my trip cheaper", "I updated the plan with a lower-cost stay."),
            ("What did I ask you earlier?", "You asked about Tokyo and cheaper hotels."),
            ("Change my destination to Paris", "I rebuilt your itinerary for Paris.")
        ]
        model_responses = [
            {"reply": answer, "updated_plan": None}
            for _, answer in scenarios
        ]
        model_responses[4]["updated_plan"] = {
            "hotels": [{"name": "Budget Guesthouse", "nightly_rate_usd": 70}],
            "budget_breakdown": {
                "stay_cost_usd": 210,
                "total_budget_usd": 1200
            }
        }
        model_responses[6]["updated_plan"] = {"destination": "Paris"}

        with patch(
            "app.main.llm_service.generate",
            side_effect=[json.dumps(result) for result in model_responses]
        ) as generate:
            responses = []
            for message, _ in scenarios:
                responses.append(main.chat_with_agent(ChatRequest(
                    trip_id="chat-trip",
                    user_id="chat-test-user",
                    destination="Tokyo",
                    duration_days=3,
                    message=message
                )))

        for response, (_, expected) in zip(responses, scenarios):
            self.assertEqual(response.reply, expected)
        self.assertEqual(responses[4].updated_plan["hotels"][0]["name"], "Budget Guesthouse")
        self.assertEqual(responses[6].updated_plan["destination"], "Paris")
        self.assertEqual(main.db_manager.get_trip("chat-trip")["destination"], "Paris")
        self.assertEqual(
            len(main.db_manager.get_chat_history("chat-test-user", "chat-trip")),
            14
        )
        self.assertEqual(main.db_manager.get_chat_history("another-user", "chat-trip"), [])
        self.assertEqual(main.db_manager.get_chat_history("chat-test-user", "another-trip"), [])

        earlier_turn_prompt = generate.call_args_list[5].args[0]
        self.assertIn("Suggest cheaper hotels", earlier_turn_prompt)
        self.assertIn("Tell me about Tokyo", earlier_turn_prompt)
        self.assertTrue(all(
            call.kwargs["allow_offline_fallback"] is False
            for call in generate.call_args_list
        ))

    def test_trip_chat_rejects_another_users_trip(self):
        self._create_trip()
        with self.assertRaises(HTTPException) as raised:
            main.chat_with_agent(ChatRequest(
                trip_id="chat-trip",
                user_id="different-user",
                message="Hi"
            ))
        self.assertEqual(raised.exception.status_code, 404)

    def test_gemini_configuration_error_is_returned_to_api(self):
        with patch(
            "app.main.llm_service.generate",
            side_effect=LLMConfigurationError(
                "Gemini is not configured. Set GEMINI_API_KEY to enable AI chat."
            )
        ):
            with self.assertRaises(HTTPException) as raised:
                main.chat_with_agent(ChatRequest(message="Hi"))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("GEMINI_API_KEY", raised.exception.detail)

    def test_invalid_model_payload_is_not_presented_as_an_answer(self):
        with patch("app.main.llm_service.generate", return_value="not valid JSON"):
            with self.assertRaises(HTTPException) as raised:
                main.chat_with_agent(ChatRequest(message="Hi"))
        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("invalid chat response", raised.exception.detail)

    def test_missing_key_requires_configuration_and_labels_offline_demo(self):
        service = GeminiLLMService(api_key="your_missing_key")
        with self.assertRaises(LLMConfigurationError):
            service.generate("Hi", allow_offline_fallback=False)
        self.assertIn(
            "[OFFLINE SIMULATION - NOT GENERATED BY GEMINI]",
            service.generate("Hi")
        )

    def test_rate_limit_and_timeout_have_specific_errors(self):
        service = GeminiLLMService(api_key="test-key")
        rate_limit = urllib.error.HTTPError(
            service.api_url, 429, "Too Many Requests", {}, io.BytesIO()
        )
        with patch("urllib.request.urlopen", side_effect=rate_limit):
            with self.assertRaises(LLMRateLimitError):
                service.generate("Hi", allow_offline_fallback=False)
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            with self.assertRaises(LLMTimeoutError):
                service.generate("Hi", allow_offline_fallback=False)


if __name__ == "__main__":
    unittest.main()
