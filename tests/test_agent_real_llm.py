"""
Real LLM Integration Test (📘 Lesson 8: Tests: fake LLM first, then a real one)

Tests the ReAct agent connected to the real Gemini LLM service provider.
If GEMINI_API_KEY is available in the environment, executes live network inference.
Otherwise, tests the service client's communication pipeline seamlessly.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.llm_service import GeminiLLMService
from app.core.react_agent import ReActAgent
from app.core.error_handler import SafeToolExecutor
from app.core.memory import MemoryStore
from app.core.safety import SafetyGate


class TestAgentWithRealLLM(unittest.TestCase):

    def setUp(self):
        self.llm_service = GeminiLLMService()
        self.tool_executor = SafeToolExecutor()
        self.memory_store = MemoryStore(storage_path=":memory:")
        self.safety_gate = SafetyGate(confirmation_cost_threshold=1000.0)

    def test_real_llm_service_initialization(self):
        """Verify LLM service provider configures correctly."""
        self.assertIsNotNone(self.llm_service)
        self.assertEqual(self.llm_service.model, "gemini-1.5-flash")

    def test_real_llm_agent_pipeline_execution(self):
        """
        Run the ReAct agent through the Gemini LLM provider pipeline (📘 L8).
        Executes Think -> Act -> Look -> Final Answer.
        """
        agent = ReActAgent(
            llm_caller=self.llm_service.generate,
            tool_executor=self.tool_executor,
            memory_store=self.memory_store,
            safety_gate=self.safety_gate,
            max_steps=6
        )

        result = agent.run(
            user_query="Plan a 3-day cultural trip to Tokyo for 2 travelers",
            user_id="user_test_real",
            destination="Tokyo",
            duration_days=3
        )

        # Verify pipeline execution completed
        self.assertIn(result["status"], ["completed", "max_steps_reached"])
        self.assertGreaterEqual(result["total_steps"], 1)
        self.assertIsNotNone(result["final_answer"])
        
        # Verify trajectory has steps with thoughts and observations
        first_step = result["trajectory"][0]
        self.assertIn("thought", first_step)
        print(f"\n[Real LLM Test Result] Steps: {result['total_steps']}, Status: {result['status']}")
        print(f"[Final Answer]: {result['final_answer'][:120]}...")


if __name__ == "__main__":
    unittest.main()

