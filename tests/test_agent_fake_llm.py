"""
Comprehensive Unit Test Suite for Lessons 1 through 7 (📘 L8: Tests: fake LLM first)

Verifies:
1. Loop: think -> act -> look (📘 L1, L3)
2. 2-4 clearly described tools (📘 L2)
3. Fixing errors when a tool fails (📘 L2)
4. Memory between tasks (📘 L4)
5. A plan before it acts (📘 L5)
6. Safety: asks you first, step limit, log (📘 L7)
"""

import sys
import os
import unittest
import tempfile
import json

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.tools import (
    search_destinations_and_attractions,
    get_weather_forecast,
    search_hotels,
    calculate_budget_allocation
)
from app.core.error_handler import SafeToolExecutor
from app.core.memory import MemoryStore
from app.core.planner import ExecutionPlan
from app.core.safety import SafetyGate
from app.core.react_agent import ReActAgent
from tests.fake_llm import FakeLLM


class TestAgentComprehensive(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory_path = os.path.join(self.temp_dir.name, "test_memory.json")
        self.audit_log_path = os.path.join(self.temp_dir.name, "test_audit.log")
        
        self.memory_store = MemoryStore(storage_path=self.memory_path)
        self.safety_gate = SafetyGate(
            confirmation_cost_threshold=500.0,
            log_file_path=self.audit_log_path
        )
        self.executor = SafeToolExecutor()

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. TEST THE 4 TOOLS (📘 L2)
    # -------------------------------------------------------------
    def test_destination_search_tool(self):
        result = search_destinations_and_attractions(city="Tokyo", category="culture")
        self.assertEqual(result["city"], "Tokyo")
        self.assertGreaterEqual(result["total_attractions_found"], 1)

    def test_weather_forecast_tool(self):
        result = get_weather_forecast(city="Paris", days=5)
        self.assertEqual(result["city"], "Paris")
        self.assertIn("temperature_celsius", result)

    def test_search_hotels_tool(self):
        result = search_hotels(city="Jaipur", budget_tier="budget", nights=3, guests=2)
        self.assertEqual(result["city"], "Jaipur")
        self.assertGreater(result["options_count"], 0)

    def test_budget_calculator_tool(self):
        result = calculate_budget_allocation(total_budget=800.0, stay_cost=250.0, activities_cost=50.0, days=3, guests=2)
        self.assertEqual(result["total_budget_usd"], 800.0)
        self.assertTrue(result["is_healthy_budget"])

    # -------------------------------------------------------------
    # 2. TEST THINK -> ACT -> LOOK LOOP (📘 L1, L3)
    # -------------------------------------------------------------
    def test_react_loop_flow(self):
        fake_llm = FakeLLM([
            'Thought: Checking weather first.\nAction: get_weather_forecast(city="Tokyo", days=3)',
            'Thought: Researching attractions.\nAction: search_destinations_and_attractions(city="Tokyo", category="all")',
            'Thought: I have the needed info.\nFinal Answer: Complete 3-day Tokyo itinerary.'
        ])
        agent = ReActAgent(llm_caller=fake_llm, tool_executor=self.executor, safety_gate=self.safety_gate)
        result = agent.run("Plan a Tokyo trip")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["total_steps"], 3)
        self.assertIn("Complete 3-day Tokyo itinerary", result["final_answer"])

    # -------------------------------------------------------------
    # 3. TEST FIXING TOOL ERRORS / SELF-CORRECTION (📘 L2)
    # -------------------------------------------------------------
    def test_tool_error_recovery(self):
        fake_llm = FakeLLM([
            'Thought: Searching Tokyoo typo.\nAction: search_destinations_and_attractions(city="Tokyoo", category="culture")',
            'Thought: Typo noticed. Correcting to Tokyo.\nAction: search_destinations_and_attractions(city="Tokyo", category="culture")',
            'Thought: Attractions gathered.\nFinal Answer: Tokyo trip finalized.'
        ])
        agent = ReActAgent(llm_caller=fake_llm, tool_executor=self.executor, safety_gate=self.safety_gate)
        result = agent.run("Plan Tokyo trip")

        self.assertEqual(result["status"], "completed")
        # Step 1 should record ToolError observation
        self.assertIn("ToolError", result["trajectory"][0]["observation"])
        # Step 2 should succeed
        self.assertIn("Success", result["trajectory"][1]["observation"])

    # -------------------------------------------------------------
    # 4. TEST MEMORY BETWEEN TASKS (📘 L4)
    # -------------------------------------------------------------
    def test_cross_task_memory(self):
        # Task 1: Save user preferences
        self.memory_store.set_preference("user_101", "dietary", "Strict Vegetarian")
        self.memory_store.set_preference("user_101", "pace", "Relaxed & cultural")
        self.memory_store.record_trip("user_101", "Kyoto", "Temple visits", 850.0)

        # Task 2: Agent runs for user_101 on a new destination
        fake_llm = FakeLLM([
            'Thought: User prefers vegetarian and relaxed pace. Finalizing plan.\nFinal Answer: Paris relaxing vegetarian plan.'
        ])
        agent = ReActAgent(
            llm_caller=fake_llm,
            tool_executor=self.executor,
            memory_store=self.memory_store,
            safety_gate=self.safety_gate
        )
        result = agent.run("Plan a weekend in Paris", user_id="user_101")

        self.assertEqual(result["status"], "completed")
        # Verify the prompt sent to LLM included recalled memory
        prompt_sent = fake_llm.prompt_history[0]
        self.assertIn("Strict Vegetarian", prompt_sent)
        self.assertIn("Relaxed & cultural", prompt_sent)
        self.assertIn("Visited Kyoto", prompt_sent)

    # -------------------------------------------------------------
    # 5. TEST UPFRONT PLANNING & SCRATCHPAD (📘 L5)
    # -------------------------------------------------------------
    def test_upfront_planning_scratchpad(self):
        plan = ExecutionPlan(destination="Paris", duration_days=3)
        scratchpad_initial = plan.get_scratchpad()
        self.assertIn("[ ] Step 2: Retrieve weather forecast for Paris", scratchpad_initial)
        
        # Mark Step 2 completed
        plan.mark_completed(2)
        scratchpad_updated = plan.get_scratchpad()
        self.assertIn("[X] Step 2: Retrieve weather forecast for Paris", scratchpad_updated)

    # -------------------------------------------------------------
    # 6. TEST SAFETY: ASKS YOU FIRST, STEP LIMIT, AUDIT LOG (📘 L7)
    # -------------------------------------------------------------
    def test_safety_step_limit(self):
        endless = ['Thought: looping.\nAction: get_weather_forecast(city="Tokyo", days=1)' for _ in range(10)]
        fake_llm = FakeLLM(endless)
        agent = ReActAgent(llm_caller=fake_llm, tool_executor=self.executor, safety_gate=self.safety_gate, max_steps=3)
        result = agent.run("Loop test")
        self.assertEqual(result["status"], "max_steps_reached")
        self.assertEqual(result["total_steps"], 3)

    def test_safety_human_confirmation_rejection(self):
        # Action with budget > $500 threshold and no human confirmation
        fake_llm = FakeLLM([
            'Thought: Calculating large budget.\nAction: calculate_budget_allocation(total_budget=1500.0, stay_cost=600.0, days=5)',
            'Thought: Safety stopped the large allocation. Adjusting.\nFinal Answer: Adjusted budget.'
        ])
        agent = ReActAgent(llm_caller=fake_llm, tool_executor=self.executor, safety_gate=self.safety_gate)
        result = agent.run("Allocate big budget")

        # Step 1 should have been paused/blocked by Safety Gate (📘 L7)
        self.assertIn("SafetyIntervention", result["trajectory"][0]["observation"])
        self.assertIn("HUMAN_CONFIRMATION_REQUIRED", result["trajectory"][0]["observation"])

    def test_safety_audit_log_written_to_disk(self):
        fake_llm = FakeLLM(['Thought: Quick plan.\nFinal Answer: Done.'])
        agent = ReActAgent(llm_caller=fake_llm, tool_executor=self.executor, safety_gate=self.safety_gate)
        agent.run("Audit log test")

        # Verify audit log exists and contains logged events
        self.assertTrue(os.path.exists(self.audit_log_path))
        with open(self.audit_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertGreaterEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertIn("timestamp", record)
        self.assertIn("event_type", record)


if __name__ == "__main__":
    unittest.main()
