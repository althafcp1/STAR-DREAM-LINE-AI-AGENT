"""
ReAct Agent Core Engine (📘 Lessons 1-7: Full Agentic System)

Integrates:
1. Think -> Act -> Look Loop (📘 L1, L3)
2. 4 Clearly Described Tools (📘 L2)
3. Fixing errors when a tool fails (📘 L2)
4. Cross-task memory (📘 L4)
5. Upfront planning & scratchpad (📘 L5)
6. Safety: asks you first, step limit, structured audit log (📘 L7)
"""

from typing import List, Dict, Any, Optional, Callable
import re
import ast
from app.core.tools import TOOL_DESCRIPTIONS, TOOL_REGISTRY
from app.core.error_handler import SafeToolExecutor
from app.core.memory import MemoryStore
from app.core.planner import ExecutionPlan
from app.core.safety import SafetyGate


class AgentStep:
    """Represents a single iteration in the Think-Act-Look cycle."""
    def __init__(self, step_number: int, thought: str, action: Optional[str] = None, observation: Optional[str] = None):
        self.step_number = step_number
        self.thought = thought
        self.action = action
        self.observation = observation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation
        }


class ReActAgent:
    """
    Autonomous ReAct Agent integrating loop, tools, error correction, memory, planning, and safety.
    """
    SYSTEM_PROMPT = """You are an expert AI Travel Planning Assistant.
You solve travel queries by cycling through: Thought -> Action -> Observation.

AVAILABLE TOOLS:
{tool_descriptions}

FORMAT RULES:
Use the following strict format for each step:

Thought: [Your step-by-step reasoning about what information is needed]
Action: tool_name(param1="val1", param2=123)

Wait for the environment to provide the Observation.
Once you have collected all required information to fulfill the user request and execution plan, output:

Thought: [I now have all information needed to finalize the travel plan]
Final Answer: [Your complete, structured travel recommendations and itinerary]
"""

    def __init__(
        self,
        llm_caller: Callable[[str], str],
        tool_executor: Optional[SafeToolExecutor] = None,
        memory_store: Optional[MemoryStore] = None,
        safety_gate: Optional[SafetyGate] = None,
        max_steps: int = 10
    ):
        self.llm_caller = llm_caller
        self.tool_executor = tool_executor or SafeToolExecutor(TOOL_REGISTRY)
        self.memory_store = memory_store or MemoryStore()
        self.safety_gate = safety_gate or SafetyGate()
        self.max_steps = max_steps
        self.steps: List[AgentStep] = []

    def _format_tools_prompt(self) -> str:
        lines = []
        for t in TOOL_DESCRIPTIONS:
            params = ", ".join([f"{k}: {v}" for k, v in t["parameters"].items()])
            lines.append(f"- {t['name']}({params}): {t['description']}")
        return "\n".join(lines)

    def _parse_action(self, action_str: str) -> tuple[Optional[str], Dict[str, Any]]:
        pattern = r"^([a-zA-Z0-9_]+)\((.*)\)$"
        match = re.match(pattern, action_str.strip())
        if not match:
            return None, {}
        
        tool_name = match.group(1)
        args_str = match.group(2).strip()
        
        if not args_str:
            return tool_name, {}

        try:
            call_code = f"func({args_str})"
            tree = ast.parse(call_code)
            call_node = tree.body[0].value  # type: ignore
            kwargs = {}
            for kw in call_node.keywords:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            return tool_name, kwargs
        except Exception as e:
            return tool_name, {"_raw_args": args_str, "_parse_error": str(e)}

    def run(
        self,
        user_query: str,
        user_id: str = "default_user",
        destination: str = "Tokyo",
        duration_days: int = 3
    ) -> Dict[str, Any]:
        """
        Executes the ReAct loop with Memory (📘 L4), Planning (📘 L5), and Safety (📘 L7).
        """
        self.steps = []
        
        # 1. MEMORY RECALL (📘 L4: Memory between tasks)
        recalled_memory = self.memory_store.format_memory_context(user_id)
        
        # 2. UPFRONT PLAN CREATION (📘 L5: A plan before it acts)
        plan = ExecutionPlan(destination=destination, duration_days=duration_days)
        scratchpad = plan.get_scratchpad()

        # Build initial prompt
        tools_doc = self._format_tools_prompt()
        system_header = self.SYSTEM_PROMPT.format(tool_descriptions=tools_doc)
        
        conversation_history = f"{system_header}\n{recalled_memory}\n{scratchpad}\nUser Query: {user_query}\n"
        
        final_answer: Optional[str] = None
        status = "in_progress"
        offline_simulation = False

        # 3. THE REACT LOOP (📘 L1, L3: think -> act -> look)
        for step_idx in range(1, self.max_steps + 1):
            # STEP LIMIT SAFEGUARD (📘 L7)
            self.safety_gate.log_event("loop_step_start", {"step": step_idx, "max_steps": self.max_steps})

            # THINK
            llm_response = self.llm_caller(conversation_history)
            if "[OFFLINE SIMULATION - NOT GENERATED BY GEMINI]" in llm_response:
                offline_simulation = True
            self.safety_gate.log_event("thought_generated", {"step": step_idx, "response": llm_response})

            # Check for Final Answer
            if "Final Answer:" in llm_response:
                parts = llm_response.split("Final Answer:", 1)
                thought_part = parts[0].replace("Thought:", "").strip()
                final_answer = parts[1].strip()
                
                step = AgentStep(step_number=step_idx, thought=thought_part, action=None, observation=None)
                self.steps.append(step)
                status = "completed"
                break

            # Parse Thought and Action
            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", llm_response, re.DOTALL)
            action_match = re.search(r"Action:\s*(.*?)(?=\n|$)", llm_response)

            thought = thought_match.group(1).strip() if thought_match else "Analyzing next step..."
            action_str = action_match.group(1).strip() if action_match else None

            if not action_str:
                step = AgentStep(step_number=step_idx, thought=thought, action="No action specified", observation="Error: Please specify an Action or Final Answer.")
                self.steps.append(step)
                conversation_history += f"Thought: {thought}\nObservation: Error: Please specify an Action or Final Answer.\n"
                continue

            tool_name, kwargs = self._parse_action(action_str)

            # SAFETY GATE: ASKS YOU FIRST (📘 L7)
            if tool_name:
                is_safe, safety_msg = self.safety_gate.check_action_safety(tool_name, kwargs)
                if not is_safe:
                    observation = f"Observation: SafetyIntervention: {safety_msg}"
                    self.safety_gate.log_event("action_blocked_by_safety", {"tool": tool_name, "reason": safety_msg})
                    step = AgentStep(step_number=step_idx, thought=thought, action=action_str, observation=observation)
                    self.steps.append(step)
                    conversation_history += f"Thought: {thought}\nAction: {action_str}\n{observation}\n"
                    continue

            # ACT & LOOK (📘 L1, L2, L3)
            if not tool_name:
                observation = f"Observation: ToolSyntaxError: Could not parse '{action_str}'."
            elif "_parse_error" in kwargs:
                observation = f"Observation: ParameterSyntaxError: {kwargs['_parse_error']}."
            else:
                # Tool execution with automatic error handling (📘 L2)
                observation = self.tool_executor.execute(tool_name, **kwargs)

            # Update Plan Scratchpad (📘 L5)
            for ps in plan.steps:
                if ps.tool_name == tool_name and not ps.completed:
                    plan.mark_completed(ps.step_id)
                    break

            step = AgentStep(step_number=step_idx, thought=thought, action=action_str, observation=observation)
            self.steps.append(step)
            self.safety_gate.log_event("tool_executed", {"step": step_idx, "tool": tool_name, "observation": observation})

            conversation_history += f"Thought: {thought}\nAction: {action_str}\n{observation}\n"

        if not final_answer:
            status = "max_steps_reached"
            final_answer = f"Execution reached step limit ({self.max_steps}). Partial itinerary compiled."
        if offline_simulation and "[OFFLINE SIMULATION - NOT GENERATED BY GEMINI]" not in final_answer:
            final_answer = (
                "[OFFLINE SIMULATION - NOT GENERATED BY GEMINI]\n"
                f"{final_answer}"
            )

        return {
            "status": status,
            "total_steps": len(self.steps),
            "final_answer": final_answer,
            "trajectory": [s.to_dict() for s in self.steps],
            "plan_progress": [s.to_dict() for s in plan.steps]
        }
