"""
Startup script for the AI Travel Planning Agent
Launches the FastAPI backend and serves the interactive frontend at http://127.0.0.1:8000
"""

import sys
import os

# Add backend directory to system path
backend_path = os.path.join(os.path.dirname(__file__), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 65)
    print("  🚀 AI Travel Planning Agent — Server Starting")
    print(f"  🌐 Open in your browser: http://{settings.HOST}:{settings.PORT}")
    print(f"  📄 API Documentation:    http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 65)
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.APP_DEBUG)


