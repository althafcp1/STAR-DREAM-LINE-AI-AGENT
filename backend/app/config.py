"""
Application Configuration & Settings (Phase 0: Environment Provisioning)
"""

import os
from pathlib import Path
from typing import Optional


class Settings:
    """
    Centralized application settings with environment variable overrides and sensible defaults.
    """
    def __init__(self):
        # Determine base directory
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent
        self.BACKEND_DIR = self.BASE_DIR / "backend"
        
        # Load .env file if it exists
        env_file = self.BACKEND_DIR / ".env"
        if not env_file.exists():
            env_file = self.BASE_DIR / ".env"
            
        if env_file.exists():
            self._load_env_file(env_file)

        # Server Configuration
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() in ("true", "1", "yes")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.HOST: str = os.getenv("HOST", "127.0.0.1")

        # LLM Settings
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        # Currency API
        self.EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

        # External API Keys
        self.OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
        self.GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

        # Agent Safety & Governance (📘 L7)
        self.MAX_AGENT_STEPS: int = int(os.getenv("MAX_AGENT_STEPS", "10"))
        self.CONFIRMATION_THRESHOLD_USD: float = float(os.getenv("REQUIRE_CONFIRMATION_THRESHOLD_USD", "500.0"))
        self.ENABLE_AUDIT_LOG: bool = os.getenv("ENABLE_AUDIT_LOG", "true").lower() in ("true", "1", "yes")

        # Database
        self.DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(self.BASE_DIR / "travel_planner.db"))

    def _load_env_file(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception:
            pass


settings = Settings()

