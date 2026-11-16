"""
Tool Error Interceptor & Self-Correction Engine (📘 Lesson 2: Fixing errors when a tool fails)

When a tool fails (e.g. invalid arguments, typo in destination, budget calculation deficit),
this module intercepts the failure and converts it into a helpful diagnostic Observation.
The agent reads this observation in the next loop cycle and performs self-correction.
"""

from typing import Dict, Any, Callable
import traceback
from app.core.tools import ToolError, TOOL_REGISTRY


class SafeToolExecutor:
    """
    Safely executes registered tools with comprehensive error handling and feedback formatting.
    """
    def __init__(self, registry: Dict[str, Callable] = TOOL_REGISTRY):
        self.registry = registry

    def execute(self, tool_name: str, **kwargs) -> str:
        """
        Executes a tool by name with provided keyword arguments.
        Returns a stringified Observation for the agent's Think-Act-Look loop.
        """
        # 1. Tool Existence Check
        if tool_name not in self.registry:
            available = ", ".join(list(self.registry.keys()))
            return (
                f"ToolError: Unknown tool '{tool_name}'. "
                f"Available tools are: [{available}]. Please check the tool name."
            )

        tool_func = self.registry[tool_name]

        # 2. Safe Execution with Targeted Error Feedback (📘 L2)
        try:
            result = tool_func(**kwargs)
            return f"Observation: Success -> {result}"
        except ToolError as te:
            # Custom domain errors (e.g. city not found, overbudget, invalid tier)
            return f"Observation: ToolError in '{tool_name}': {str(te)}"
        except TypeError as te:
            # Missing or unexpected argument types
            return (
                f"Observation: ToolArgumentError in '{tool_name}': {str(te)}. "
                "Please verify your parameter names and types against the tool schema."
            )
        except ValueError as ve:
            return f"Observation: ToolValueError in '{tool_name}': {str(ve)}."
        except Exception as e:
            # Generic fallback to prevent crashing the entire agent system
            return (
                f"Observation: UnexpectedError in '{tool_name}': {str(e)}. "
                "Please try an alternative parameter or fallback tool."
            )

