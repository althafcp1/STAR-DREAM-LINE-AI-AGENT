"""execute_phase7.py – End‑to‑End Testing & QA

This script performs a comprehensive integration test of the entire AI Travel Planning
stack:
  • Starts the FastAPI server in a subprocess.
  • Waits for the health‑check endpoint.
  • Executes a series of API calls that cover the main user flows:
      – trip planning (POST /api/trip/plan)
      – retrieve trip (GET /api/trip/{id})
      – chat interaction (POST /api/chat)
      – PDF generation (GET /api/trip/{id}/pdf)
      – a simple load test (multiple rapid plan requests).
  • Reports success/failure for each step and exits with a non‑zero code if any
     verification fails.
  • Cleans up by terminating the server process.
"""
import subprocess, sys, time, json, urllib.request, urllib.error, urllib.parse

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def start_server():
    """Launch the FastAPI server via run_server.py (ensures proper import paths)."""
    project_root = os.path.abspath(os.path.dirname(__file__))
    cmd = [sys.executable, os.path.join(project_root, "run_server.py")]
    return subprocess.Popen(cmd, cwd=project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """Launch the FastAPI server via run_server.py (ensures proper import paths)."""
    cmd = [sys.executable, "run_server.py"]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """Launch uvicorn as a background process."""
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app",
           "--host", SERVER_HOST, "--port", str(SERVER_PORT), "--log-level", "error"]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

def wait_for_endpoint(url, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = http_get(url)
            if getattr(resp, "status", None) == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    server = start_server()
    try:
        if not wait_for_endpoint(f"{BASE_URL}/api/health"):
            print("❌ Health check failed – server not reachable")
            sys.exit(1)
        print("🟢 Server reachable")

        # 1️⃣ Basic trip planning
        plan_payload = {
            "user_id": "e2e_user",
            "destination": "Paris",
            "duration_days": 4,
            "budget": 1500,
            "travelers_count": 2,
            "accommodation_type": "mid",
            "travel_preferences": "culture"
        }
        resp = http_post(f"{BASE_URL}/api/trip/plan", plan_payload)
        if getattr(resp, "status", None) != 200:
            print("❌ /api/trip/plan failed", getattr(resp, "status", None))
            sys.exit(1)
        plan_data = json.loads(resp.read().decode())
        trip_id = plan_data.get("trip_id")
        print("✅ Trip planned – id:", trip_id)

        # 2️⃣ Retrieve trip
        resp = http_get(f"{BASE_URL}/api/trip/{trip_id}")
        if getattr(resp, "status", None) != 200:
            print("❌ GET /api/trip/{id} failed")
            sys.exit(1)
        trip_info = json.loads(resp.read().decode())
        if not trip_info.get("daily_itinerary"):
            print("❌ Itinerary missing in trip data")
            sys.exit(1)
        print("✅ Trip retrieved with itinerary")

        # 3️⃣ Chat interaction
        chat_payload = {"message": "Any museum tips?", "trip_id": trip_id, "destination": "Paris"}
        resp = http_post(f"{BASE_URL}/api/chat", chat_payload)
        if getattr(resp, "status", None) != 200:
            print("❌ /api/chat failed")
            sys.exit(1)
        chat_reply = json.loads(resp.read().decode()).get("reply", "")
        print("✅ Chat reply snippet:", (chat_reply[:60] + "…") if chat_reply else "empty")

        # 4️⃣ PDF generation
        resp = http_get(f"{BASE_URL}/api/trip/{trip_id}/pdf")
        if getattr(resp, "status", None) != 200 or resp.headers.get("Content-Type") != "application/pdf" or len(resp.read()) == 0:
            print("❌ PDF generation failed")
            sys.exit(1)
        print("✅ PDF generated successfully")

        # 5️⃣ Light load test – submit 3 additional plans quickly
        for i in range(3):
            extra_payload = plan_payload.copy()
            extra_payload["destination"] = f"City{i}"
            resp = http_post(f"{BASE_URL}/api/trip/plan", extra_payload)
            if getattr(resp, "status", None) != 200:
                print(f"❌ Load test plan {i} failed")
                sys.exit(1)
        print("✅ Load test passed (3 rapid plans)")

        print("\n✅ End‑to‑End Phase 7 verification succeeded.")
    finally:
        server.terminate()
        server.wait()
        print("🛑 Server stopped.")

if __name__ == "__main__":
    main()
