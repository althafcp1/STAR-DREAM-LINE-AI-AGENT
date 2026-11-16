import subprocess, os, sys, json

def run_uvicorn(port):
    env = os.environ.copy()
    env['APP_DEBUG'] = 'false'
    env['APP_ENV'] = 'production'
    cmd = [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error']
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print('returncode', result.returncode)
    print('stdout:\n', result.stdout)
    print('stderr:\n', result.stderr)

if __name__ == '__main__':
    run_uvicorn(8009)

