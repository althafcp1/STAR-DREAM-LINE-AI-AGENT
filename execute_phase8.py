"""execute_phase8.py – Deployment & Production Readiness Verification

This script checks that the project is ready for production deployment:
  1️⃣ Confirms the presence of a Dockerfile and (optionally) a docker‑compose file.
  2️⃣ Starts the FastAPI server in *production mode* (APP_DEBUG=false).
  3️⃣ Performs a minimal health‑check and a single trip‑plan request to ensure the
     backend works with production settings.
  4️⃣ Cleans up the server process.

All steps run using only the standard library (urllib) to avoid external
dependencies.
"""
import os, sys, subprocess, time, json, urllib.request, urllib.error, urllib.parse

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "Dockerfile")
COMPOSE_PATH = os.path.join(PROJECT_ROOT, "docker-compose.yml")

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def check_files():
    missing = []
    if not os.path.isfile(DOCKERFILE_PATH):
        missing.append("Dockerfile")
    if not os.path.isfile(COMPOSE_PATH):
        missing.append("docker‑compose.yml (optional but recommended)")
    if missing:
        print("⚠️ Missing files:", ", ".join(missing))
    else:
        print("✅ Required files present")

def start_server_prod():
    """Launch FastAPI directly with uvicorn in production mode.
    Logs are written to 'phase8_server.log' for diagnostics.
    """
    env = os.environ.copy()
    env["APP_DEBUG"] = "false"
    env["APP_ENV"] = "production"
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "backend.app.main:app",
        "--host", SERVER_HOST,
        "--port", str(SERVER_PORT),
        "--log-level", "error"
    ]
    log_path = os.path.join(PROJECT_ROOT, "phase8_server.log")
    # Open log file for both stdout and stderr
    log_file = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env,
                            stdout=log_file, stderr=subprocess.STDOUT)

    """Launch the FastAPI server via run_server.py with production settings."""
    env = os.environ.copy()
    env["APP_DEBUG"] = "false"
    env["APP_ENV"] = "production"
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, "run_server.py")]
    return subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """Launch the FastAPI server with production settings (APP_DEBUG=false)."""
    env = os.environ.copy()
    env["APP_DEBUG"] = "false"
    env["APP_ENV"] = "production"
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app",
           "--host", SERVER_HOST, "--port", str(SERVER_PORT), "--log-level", "error"]
    return subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """Launch the FastAPI server with production settings (APP_DEBUG=false)."""
    # Force production env vars for this run
    env = os.environ.copy()
    env["APP_DEBUG"] = "false"
    env["APP_ENV"] = "production"
    cmd = [sys.executable, "run_server.py"]
    return subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def http_get(url, timeout=10):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp
    except urllib.error.HTTPError as e:
        return e
    except Exception as e:
        raise RuntimeError(f"GET {url} failed: {e}")

def http_post(url, data, timeout=10):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp
    except urllib.error.HTTPError as e:
        return e
    except Exception as e:
        raise RuntimeError(f"POST {url} failed: {e}")

def wait_for_health(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = http_get(f"{BASE_URL}/api/health")
            if getattr(resp, "status", None) == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    check_files()
    server = start_server_prod()
    try:
        if not wait_for_health():
            print("❌ Production health‑check failed – server not reachable")
            sys.exit(1)
        print("🟢 Production server reachable")

        # Minimal trip plan request to ensure DB and config load correctly
        payload = {
            "user_id": "prod_test",
            "destination": "Berlin",
            "duration_days": 2,
            "budget": 800,
            "travelers_count": 1,
            "accommodation_type": "budget",
            "travel_preferences": "culture"
        }
        resp = http_post(f"{BASE_URL}/api/trip/plan", payload)
        if getattr(resp, "status", None) != 200:
            print("❌ Production trip planning endpoint failed", getattr(resp, "status", None))
            sys.exit(1)
        data = json.loads(resp.read().decode())
        print("✅ Production trip planning succeeded – trip_id:", data.get("trip_id"))
    finally:
        server.terminate()
        server.wait()
        print("🛑 Production server stopped")

if __name__ == "__main__":
    main()
