import os, sys, traceback
sys.path.append(os.getcwd())
try:
    from backend.app.main import app
    print('FastAPI app imported successfully')
    print('Routes:')
    for route in app.routes:
        print(f'  {route.path} -> {route.name}')
except Exception as e:
    print('Import error:', e)
    traceback.print_exc()

