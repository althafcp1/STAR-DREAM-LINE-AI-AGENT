"""
Cross-Task Persistent Memory Store (📘 Lesson 4: Memory between tasks)

Maintains user preferences and knowledge across distinct tasks/sessions:
1. Stores user profile (dietary restrictions, preferred hotel tiers, activity interests).
2. Records past completed trips and user notes.
3. Injects relevant historical context into the agent's prompt on new tasks.
"""

from typing import Dict, Any, List, Optional
import json
import os


class MemoryStore:
    """
    Persistent memory store using disk-backed JSON storage.
    Enables agents to remember user traits and history across separate runs.
    """
    def __init__(self, storage_path: str = "travel_agent_memory.json"):
        self.storage_path = storage_path
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.storage_path == ":memory:":
            return {}
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        if self.storage_path == ":memory:":
            return
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MemoryStore Warning] Could not save memory: {e}")


    def _get_user_bucket(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self._data:
            self._data[user_id] = {
                "preferences": {},
                "past_trips": []
            }
        return self._data[user_id]

    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """Saves a user preference (e.g. dietary='vegetarian', hotel_style='boutique')."""
        bucket = self._get_user_bucket(user_id)
        bucket["preferences"][key] = value
        self._save()

    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Retrieves all stored preferences for a user."""
        return self._get_user_bucket(user_id).get("preferences", {})

    def record_trip(self, user_id: str, destination: str, summary: str, total_spent: float) -> None:
        """Records a completed trip into long-term user history."""
        bucket = self._get_user_bucket(user_id)
        bucket["past_trips"].append({
            "destination": destination,
            "summary": summary,
            "total_spent_usd": total_spent
        })
        self._save()

    def get_trip_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves past trip history for a user."""
        return self._get_user_bucket(user_id).get("past_trips", [])

    def format_memory_context(self, user_id: str) -> str:
        """
        Formats recalled memory into an injection prompt for the agent (📘 L4).
        """
        bucket = self._get_user_bucket(user_id)
        prefs = bucket.get("preferences", {})
        trips = bucket.get("past_trips", [])

        if not prefs and not trips:
            return ""

        lines = ["[RECALLED MEMORY FROM PREVIOUS TASKS]"]
        if prefs:
            lines.append("User Preferences:")
            for k, v in prefs.items():
                lines.append(f" - {k.replace('_', ' ').title()}: {v}")
        if trips:
            lines.append(f"Past Trips Completed ({len(trips)}):")
            for t in trips[-3:]:  # Most recent 3
                lines.append(f" - Visited {t['destination']}: {t['summary']} (Spent: ${t['total_spent_usd']})")
        lines.append("[END OF RECALLED MEMORY]\n")
        return "\n".join(lines)

