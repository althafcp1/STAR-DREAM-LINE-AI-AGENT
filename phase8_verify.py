import os, sys, subprocess, time, urllib.request, json, signal, pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
log_path = PROJECT_ROOT / 'phase8_server.log'
# Ensure log is empty
if log_path.exists():
    log_path.unlink()

env = os.environ.copy()
env['APP_DEBUG'] = 'false'
env['APP_ENV'] = 'production'

# Start uvicorn server
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000', '--log-level', 'error'], cwd=str(PROJECT_ROOT), env=env, stdout=open(log_path, 'w', encoding='utf-8'), stderr=subprocess.STDOUT)

# Health check loop (max 30s)
healthy = False
deadline = time.time() + 30
while time.time() < deadline:
    # if process exited, break early
    if proc.poll() is not None:
        break
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2) as resp:
            if resp.status == 200:
                healthy = True
                break
    except Exception:
        time.sleep(0.5)

print('HEALTH', healthy)

if not healthy:
    # Print first few lines of log for diagnostics
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = [next(f) for _ in range(10)]
        print('LOG SNIPPET')
        print(''.join(lines))
    except Exception as e:
        print('Failed to read log:', e)

# If server still running, continue testing endpoints
if healthy:
    base = 'http://127.0.0.1:8000'
    # root endpoint
    try:
        with urllib.request.urlopen(base + '/', timeout=5) as resp:
            print('ROOT', resp.status)
    except Exception as e:
        print('ROOT error', e)
    # trip plan
    payload = {
        "user_id": "prod_test2",
        "destination": "Paris",
        "duration_days": 3,
        "budget": 1200,
        "travelers_count": 2,
        "accommodation_type": "mid",
        "travel_preferences": "culture"
    }
    req = urllib.request.Request(base + '/api/trip/plan', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            print('PLAN', resp.status, data.get('trip_id'))
            trip_id = data.get('trip_id')
    except Exception as e:
        print('PLAN error', e)
        trip_id = None
    if trip_id:
        # get trip
        try:
            with urllib.request.urlopen(base + f'/api/trip/{trip_id}', timeout=5) as resp:
                print('GET_TRIP', resp.status)
        except Exception as e:
            print('GET_TRIP error', e)
        # pdf
        try:
            with urllib.request.urlopen(base + f'/api/trip/{trip_id}/pdf', timeout=10) as resp:
                print('PDF', resp.status, resp.headers.get('Content-Type'))
        except Exception as e:
            print('PDF error', e)

# Clean up server
if proc.poll() is None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()
print('SERVER STOPPED')

