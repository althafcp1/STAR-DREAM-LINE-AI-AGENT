"""
Multi-Agent Team Collaboration Tests (⭐ Bonus: Lesson 6: A Team of Agents)

Verifies:
1. Supervisor coordinates 5 worker agents.
2. TeamState aggregates data across all domains.
3. Supervisor validates outputs and produces the final synthesized itinerary.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.multi_agent.supervisor import TravelManagerSupervisor


class TestMultiAgentTeam(unittest.TestCase):

    def setUp(self):
        self.supervisor = TravelManagerSupervisor()

    def test_multi_agent_collaboration_tokyo(self):
        """Verify full team of agents collaborates to plan a Tokyo trip."""
        result = self.supervisor.plan_trip(
            query="Plan a 3-day trip to Tokyo for 2 people with a $1200 budget",
            destination="Tokyo",
            duration_days=3,
            budget=1200.0,
            travelers=2
        )

        # 1. Verify Destination Agent contributed
        self.assertIsNotNone(result["destination_data"])
        self.assertGreater(result["destination_data"]["total_attractions_found"], 0)

        # 2. Verify Weather Agent contributed
        self.assertIsNotNone(result["weather_data"])
        self.assertEqual(result["weather_data"]["city"], "Tokyo")

        # 3. Verify Hotel Agent contributed
        self.assertIsNotNone(result["hotel_data"])
        self.assertGreater(result["hotel_data"]["options_count"], 0)

        # 4. Verify Budget Agent contributed
        self.assertIsNotNone(result["budget_breakdown"])
        self.assertGreater(result["budget_breakdown"]["emergency_buffer_usd"], 0)

        # 5. Verify Itinerary Agent created 3 daily schedules
        self.assertIsNotNone(result["daily_schedule"])
        self.assertEqual(len(result["daily_schedule"]), 3)

        # 6. Verify Supervisor synthesized the final report
        self.assertIsNotNone(result["final_report"])
        self.assertIn("Personalized Travel Plan: Tokyo", result["final_report"])

        # 7. Verify Team Activity Logs captured all agents
        team_logs = result["team_logs"]
        agents_logged = {log["agent"] for log in team_logs}
        expected_agents = {
            "Travel Manager Supervisor",
            "Destination Research Agent",
            "Weather Forecast Agent",
            "Hotel Accommodation Agent",
            "Budget Planning Agent",
            "Itinerary Scheduling Agent"
        }
        self.assertTrue(expected_agents.issubset(agents_logged))
        print("\n[Multi-Agent Team Test] Successfully coordinated all 6 agents!")


if __name__ == "__main__":
    unittest.main()

