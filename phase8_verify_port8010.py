import os, sys, subprocess, time, urllib.request, json, pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
log_path = PROJECT_ROOT / 'phase8_server_8010.log'
if log_path.exists():
    log_path.unlink()

env = os.environ.copy()
env['APP_DEBUG'] = 'false'
env['APP_ENV'] = 'production'
# Use a non-standard port to avoid conflicts
port = '8010'
proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', port, '--log-level', 'error'], cwd=str(PROJECT_ROOT), env=env, stdout=open(log_path, 'w', encoding='utf-8'), stderr=subprocess.STDOUT)

def health_check():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False

healthy = False
deadline = time.time() + 30
while time.time() < deadline:
    if proc.poll() is not None:
        break
    if health_check():
        healthy = True
        break
    time.sleep(0.5)
print('HEALTH', healthy)
if not healthy:
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            snippet = ''.join([next(f) for _ in range(20)])
        print('LOG SNIPPET')
        print(snippet)
    except Exception as e:
        print('Failed to read log:', e)
else:
    base = f'http://127.0.0.1:{port}'
    # root
    try:
        with urllib.request.urlopen(base + '/', timeout=5) as resp:
            print('ROOT', resp.status)
    except Exception as e:
        print('ROOT error', e)
    # plan
    payload = {"user_id":"prod_test3","destination":"Rome","duration_days":2,"budget":900,"travelers_count":1,"accommodation_type":"budget","travel_preferences":"history"}
    req = urllib.request.Request(base + '/api/trip/plan', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            print('PLAN', resp.status, data.get('trip_id'))
            trip_id = data.get('trip_id')
    except Exception as e:
        print('PLAN error', e)
        trip_id = None
    if trip_id:
        try:
            with urllib.request.urlopen(base + f'/api/trip/{trip_id}', timeout=5) as resp:
                print('GET_TRIP', resp.status)
        except Exception as e:
            print('GET_TRIP error', e)
        try:
            with urllib.request.urlopen(base + f'/api/trip/{trip_id}/pdf', timeout=10) as resp:
                print('PDF', resp.status, resp.headers.get('Content-Type'))
        except Exception as e:
            print('PDF error', e)

if proc.poll() is None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()
print('SERVER STOPPED')

