"""
Upfront Planner & Scratchpad (📘 Lesson 5: A plan before it acts)

Forces the agent to formulate an explicit, structured plan before acting:
1. Decomposes the user's travel request into ordered sub-goals.
2. Tracks progress via an execution scratchpad with checkbox statuses.
3. Informs the agent of its current progress and remaining tasks.
"""

from typing import List, Dict, Any


class PlanStep:
    def __init__(self, step_id: int, description: str, tool_name: str, completed: bool = False):
        self.step_id = step_id
        self.description = description
        self.tool_name = tool_name
        self.completed = completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "tool_name": self.tool_name,
            "completed": self.completed
        }


class ExecutionPlan:
    """
    Manages structured steps and provides an active scratchpad view.
    """
    def __init__(self, destination: str, duration_days: int):
        self.destination = destination
        self.duration_days = duration_days
        self.steps: List[PlanStep] = self._create_initial_plan()

    def _create_initial_plan(self) -> List[PlanStep]:
        return [
            PlanStep(1, f"Recall user preferences and prior trip memory for context", "memory"),
            PlanStep(2, f"Retrieve weather forecast for {self.destination} to adapt activities", "get_weather_forecast"),
            PlanStep(3, f"Research top attractions and sights in {self.destination}", "search_destinations_and_attractions"),
            PlanStep(4, f"Search suitable accommodations within budget in {self.destination}", "search_hotels"),
            PlanStep(5, f"Calculate budget allocation, emergency buffer, and food allowance", "calculate_budget_allocation"),
            PlanStep(6, f"Synthesize day-by-day itinerary and recommendations into final answer", "synthesize")
        ]

    def mark_completed(self, step_id: int) -> None:
        for s in self.steps:
            if s.step_id == step_id:
                s.completed = True
                break

    def get_scratchpad(self) -> str:
        """
        Formats the current plan into a Markdown checkbox scratchpad for the agent's prompt (📘 L5).
        """
        lines = ["\n[EXECUTION PLAN & PROGRESS SCRATCHPAD]"]
        for s in self.steps:
            box = "[X]" if s.completed else "[ ]"
            lines.append(f"{box} Step {s.step_id}: {s.description} ({s.tool_name})")
        lines.append("[END OF PLAN]\n")
        return "\n".join(lines)

    def is_complete(self) -> bool:
        return all(s.completed for s in self.steps)

