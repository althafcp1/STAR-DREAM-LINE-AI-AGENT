"""
Safety Guardrails & Governance (📘 Lesson 7: Safety: asks you first, step limit, log)

Enforces safety controls on agent actions:
1. ASKS YOU FIRST (Human-in-the-Loop): Requires explicit user authorization before
   executing high-cost or binding actions (e.g., booking confirmation, spending > threshold).
2. STEP LIMIT: Hard cap on loop iterations to prevent infinite loops and runaway compute.
3. STRUCTURED AUDIT LOG: Comprehensive telemetry tracking thoughts, actions, and safety gates.
"""

from typing import Dict, Any, Optional, Callable
import datetime
import json
import os


class SafetyGate:
    """
    Evaluates actions against safety policies and handles Human-in-the-Loop approvals (📘 L7).
    """
    def __init__(
        self,
        confirmation_cost_threshold: float = 500.0,
        confirmation_callback: Optional[Callable[[str], bool]] = None,
        log_file_path: str = "agent_safety_audit.log"
    ):
        self.confirmation_cost_threshold = confirmation_cost_threshold
        self.confirmation_callback = confirmation_callback
        self.log_file_path = log_file_path
        self._audit_records = []

    def check_action_safety(self, action_name: str, kwargs: Dict[str, Any]) -> tuple[bool, str]:
        """
        Evaluates whether an action requires explicit human confirmation.
        Returns: (is_approved, explanation)
        """
        # Rule 1: Direct booking confirmation always requires human consent
        if "book" in action_name.lower() or "reserve" in action_name.lower():
            prompt_msg = f"Confirmation Required: Attempting to execute booking action '{action_name}' with details {kwargs}. Approve? (yes/no)"
            return self._request_human_confirmation(prompt_msg)

        # Rule 2: Budget spending exceeding threshold requires confirmation
        stay_cost = kwargs.get("stay_cost", 0.0) or kwargs.get("total_budget", 0.0)
        if isinstance(stay_cost, (int, float)) and stay_cost > self.confirmation_cost_threshold:
            prompt_msg = (
                f"Financial Confirmation Required: Total cost of ${stay_cost:.2f} exceeds "
                f"the safety threshold (${self.confirmation_cost_threshold:.2f}). Proceed with allocation? (yes/no)"
            )
            return self._request_human_confirmation(prompt_msg)

        # Action is safe to execute autonomously
        return True, "Action approved by safety policy."

    def _request_human_confirmation(self, prompt_message: str) -> tuple[bool, str]:
        """Invokes human-in-the-loop callback if provided, or pauses for authorization."""
        if self.confirmation_callback:
            approved = self.confirmation_callback(prompt_message)
            if approved:
                return True, f"Action authorized by user: {prompt_message}"
            else:
                return False, f"Action rejected by user: {prompt_message}"
        
        # If no callback provided, default to pausing and alerting
        return False, f"HUMAN_CONFIRMATION_REQUIRED: {prompt_message}"

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Appends an event to the persistent structured audit log (📘 L7).
        """
        record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details
        }
        self._audit_records.append(record)
        
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[Safety Audit Log Warning] Could not write to audit log: {e}")

