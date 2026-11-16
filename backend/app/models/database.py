"""
Database Persistence Layer (Phase 2: Database Setup & Data Schemas)

Provides lightweight, robust SQLite persistence for:
1. Trip Plans (TripRecord): Stores all finalized itineraries, budgets, and weather data.
2. User Long-Term Memory (UserMemoryRecord): Persists travel preferences across sessions (📘 L4).
3. Audit Log Entries (AuditRecord): Tracks safety decisions and tool executions (📘 L7).
"""

import sqlite3
import json
import datetime
import os
import contextlib
from typing import Dict, Any, List, Optional


class DatabaseManager:
    """
    Manages local SQLite database operations with automatic table creation and schema validation.
    """
    def __init__(self, db_path: str = "travel_planner.db"):
        self.db_path = db_path
        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


    def _init_db(self) -> None:
        """Initializes tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Trips Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_city TEXT,
                    duration_days INTEGER NOT NULL,
                    total_budget REAL NOT NULL,
                    travelers_count INTEGER NOT NULL,
                    weather_summary TEXT,
                    hotels_json TEXT,
                    budget_breakdown TEXT,
                    daily_itinerary TEXT,
                    final_report TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. User Preferences Memory Table (📘 L4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT NOT NULL,
                    pref_key TEXT NOT NULL,
                    pref_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, pref_key)
                )
            """)

            # 3. Agent Audit Log Table (📘 L7)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id TEXT,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    trip_id TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
                ON chat_messages (user_id, trip_id, message_id)
            """)
            conn.commit()

    # -------------------------------------------------------------
    # Trip CRUD Operations
    # -------------------------------------------------------------
    def save_trip(self, trip_id: str, user_id: str, plan_data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trips (
                    trip_id, user_id, destination, departure_city, duration_days,
                    total_budget, travelers_count, weather_summary, hotels_json,
                    budget_breakdown, daily_itinerary, final_report
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trip_id,
                user_id,
                plan_data.get("destination", "Unknown"),
                plan_data.get("departure_city", "San Francisco"),
                plan_data.get("duration_days", 3),
                plan_data.get("budget", 1000.0),
                plan_data.get("travelers", 2),
                json.dumps(plan_data.get("weather_summary", {})),
                json.dumps(plan_data.get("hotels", [])),
                json.dumps(plan_data.get("budget_breakdown", {})),
                json.dumps(plan_data.get("daily_itinerary", [])),
                plan_data.get("final_report", "")
            ))
            conn.commit()

    def get_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "trip_id": row["trip_id"],
                "user_id": row["user_id"],
                "destination": row["destination"],
                "departure_city": row["departure_city"],
                "duration_days": row["duration_days"],
                "budget": row["total_budget"],
                "travelers": row["travelers_count"],
                "weather_summary": json.loads(row["weather_summary"] or "{}"),
                "hotels": json.loads(row["hotels_json"] or "[]"),
                "budget_breakdown": json.loads(row["budget_breakdown"] or "{}"),
                "daily_itinerary": json.loads(row["daily_itinerary"] or "[]"),
                "final_report": row["final_report"],
                "created_at": row["created_at"]
            }

    def list_trips_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trip_id, destination, duration_days, total_budget, created_at FROM trips WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_chat_history(
        self,
        user_id: str,
        trip_id: Optional[str],
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Return the most recent messages for one user's trip conversation."""
        conversation_trip_id = trip_id or ""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content FROM (
                    SELECT message_id, role, content
                    FROM chat_messages
                    WHERE user_id = ? AND trip_id = ?
                    ORDER BY message_id DESC
                    LIMIT ?
                )
                ORDER BY message_id ASC
            """, (user_id, conversation_trip_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def save_chat_turn(
        self,
        user_id: str,
        trip_id: Optional[str],
        user_message: str,
        assistant_message: str
    ) -> None:
        """Persist a successful user/assistant exchange in the scoped conversation."""
        conversation_trip_id = trip_id or ""
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO chat_messages (user_id, trip_id, role, content)
                VALUES (?, ?, ?, ?)
            """, [
                (user_id, conversation_trip_id, "user", user_message),
                (user_id, conversation_trip_id, "assistant", assistant_message)
            ])
            conn.commit()

    # -------------------------------------------------------------
    # User Memory Operations (📘 L4)
    # -------------------------------------------------------------
    def set_user_memory(self, user_id: str, key: str, value: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            val_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            cursor.execute("""
                INSERT OR REPLACE INTO user_memory (user_id, pref_key, pref_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, key, val_str))
            conn.commit()

    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pref_key, pref_value FROM user_memory WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            result = {}
            for r in rows:
                k, v = r["pref_key"], r["pref_value"]
                try:
                    result[k] = json.loads(v)
                except Exception:
                    result[k] = v
            return result

    # -------------------------------------------------------------
    # Audit Logging (📘 L7)
    # -------------------------------------------------------------
    def log_audit(self, trip_id: Optional[str], event_type: str, details: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (trip_id, event_type, details_json)
                VALUES (?, ?, ?)
            """, (trip_id, event_type, json.dumps(details)))
            conn.commit()

    def count_records(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM trips")
            trips_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_memory")
            mem_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM audit_logs")
            audit_count = cursor.fetchone()[0]
            return {
                "trips_count": trips_count,
                "user_memory_count": mem_count,
                "audit_logs_count": audit_count
            }

    def close(self) -> None:
        """Closes any active database resources."""
        pass
