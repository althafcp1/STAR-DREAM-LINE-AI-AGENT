"""execute_phase6.py – Frontend & Backend Integration Verification

This script starts the FastAPI server, checks that the static frontend is served, and validates the core API
endpoints required for Phase 6 (trip planning, chat interaction, and PDF export).
It runs the server in a subprocess, performs a series of HTTP requests using the built‑in ``urllib`` library,
prints a concise summary for each step, and finally terminates the server.
"""
import subprocess, sys, time, json, urllib.request, urllib.error, urllib.parse

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def start_server():
    """Launch uvicorn as a background process using `python -m uvicorn` for reliability."""
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", SERVER_HOST, "--port", str(SERVER_PORT), "--log-level", "error"]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    """Launch uvicorn as a background process."""
    cmd = [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", SERVER_HOST, "--port", str(SERVER_PORT)]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def http_get(url, timeout=10):
    """Perform a GET request, returning a response-like object."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp
    except urllib.error.HTTPError as e:
        return e
    except Exception as e:
        raise RuntimeError(f"GET {url} failed: {e}")

def http_post(url, data_dict, timeout=10):
    """POST JSON data and return the response object."""
    payload = json.dumps(data_dict).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp
    except urllib.error.HTTPError as e:
        return e
    except Exception as e:
        raise RuntimeError(f"POST {url} failed: {e}")

def wait_for_endpoint(url, timeout=10):
    """Poll until a GET returns HTTP 200 or the timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = http_get(url)
            if getattr(resp, "status", None) == 200:
                return resp
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Timeout waiting for {url}")

def main():
    server = start_server()
    try:
        # Wait for health check to confirm API is up
        wait_for_endpoint(f"{BASE_URL}/api/health", timeout=30)
        print("🟢 FastAPI server is running.")

        # 1️⃣ Verify static frontend at root
        resp = http_get(BASE_URL + "/")
        print("Root page status:", getattr(resp, "status", None), "OK" if getattr(resp, "status", None) == 200 else "FAIL")

        # 2️⃣ Submit a sample trip planning request
        plan_payload = {
            "user_id": "test_user",
            "destination": "Tokyo",
            "duration_days": 3,
            "budget": 1200,
            "travelers_count": 2,
            "accommodation_type": "budget",
            "travel_preferences": "culture"
        }
        resp = http_post(f"{BASE_URL}/api/trip/plan", plan_payload)
        print("Plan endpoint status:", getattr(resp, "status", None))
        plan_data = json.loads(resp.read().decode()) if getattr(resp, "status", None) == 200 else {}
        trip_id = plan_data.get("trip_id")
        print("  ↳ trip_id:", trip_id)

        # 3️⃣ Retrieve the generated trip
        if trip_id:
            resp = http_get(f"{BASE_URL}/api/trip/{trip_id}")
            trip_info = json.loads(resp.read().decode()) if getattr(resp, "status", None) == 200 else {}
            print("Get trip status:", getattr(resp, "status", None), "itinerary present" if trip_info.get("daily_itinerary") else "no itinerary")

            # 4️⃣ Chat interaction test
            chat_payload = {"message": "What about the weather?", "trip_id": trip_id, "destination": "Tokyo"}
            resp = http_post(f"{BASE_URL}/api/chat", chat_payload)
            chat_reply = json.loads(resp.read().decode()).get("reply") if getattr(resp, "status", None) == 200 else ""
            snippet = (chat_reply[:60] + "...") if chat_reply else "none"
            print("Chat endpoint status:", getattr(resp, "status", None), "reply snippet:", snippet)

            # 5️⃣ PDF download verification
            resp = http_get(f"{BASE_URL}/api/trip/{trip_id}/pdf")
            pdf_ok = getattr(resp, "status", None) == 200 and resp.headers.get("Content-Type") == "application/pdf" and len(resp.read()) > 0
            print("PDF download status:", getattr(resp, "status", None), "OK" if pdf_ok else "FAIL")
        else:
            print("⚠️ Planning request failed – skipping further checks.")
    finally:
        server.terminate()
        server.wait()
        print("🛑 FastAPI server stopped.")

if __name__ == "__main__":
    main()
