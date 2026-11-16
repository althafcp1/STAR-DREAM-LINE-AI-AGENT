"""
Deterministic Fake LLM for Testing (📘 Lesson 8: Tests: fake LLM first)

Simulates LLM responses predictably:
1. Scripted sequence mode: returns predetermined sequence of (Thought, Action) steps.
2. Dynamic mock mode: analyzes prompt context and generates matching ReAct responses.
"""

from typing import List, Optional


class FakeLLM:
    """
    A programmable, deterministic LLM simulator for verifying agent loops,
    tool calling, self-correction, and safety mechanisms without external API dependencies.
    """
    def __init__(self, responses: Optional[List[str]] = None):
        self.responses: List[str] = responses or []
        self.call_count: int = 0
        self.prompt_history: List[str] = []

    def set_responses(self, responses: List[str]) -> None:
        self.responses = responses
        self.call_count = 0

    def __call__(self, prompt: str) -> str:
        self.prompt_history.append(prompt)
        
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return response
        
        # Default fallback response if scripted responses are exhausted
        return (
            "Thought: I have finished evaluating all available information.\n"
            "Final Answer: Travel plan generated successfully."
        )

