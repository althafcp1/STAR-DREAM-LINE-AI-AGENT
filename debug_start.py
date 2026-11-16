import os, sys, uvicorn, traceback
os.environ['APP_DEBUG']='false'
os.environ['APP_ENV']='production'
try:
    uvicorn.run('backend.app.main:app', host='127.0.0.1', port=8003, log_level='error')
except Exception as e:
    print('Uvicorn failed:', e)
    traceback.print_exc()

