import urllib.request, sys, time

BASE = 'http://127.0.0.1:8000'

# Wait for server
healthy = False
for _ in range(30):
    try:
        with urllib.request.urlopen(BASE + '/api/health', timeout=2) as r:
            if r.status == 200:
                healthy = True
                break
    except Exception:
        time.sleep(0.5)

if not healthy:
    print('FAIL: server not reachable')
    sys.exit(1)
print('OK  /api/health -> 200')

checks = [
    ('/', 'GET', None),
    ('/static/css/styles.css', 'GET', None),
    ('/static/assets/dreamline-logo.png', 'GET', None),
]

results = []
for path, method, body in checks:
    try:
        req = urllib.request.Request(BASE + path, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            ct = r.headers.get('Content-Type', '')
            results.append((path, r.status, ct[:40]))
    except urllib.error.HTTPError as e:
        results.append((path, e.code, 'HTTPError'))
    except Exception as e:
        results.append((path, 'ERR', str(e)[:40]))

for path, status, ct in results:
    icon = 'OK ' if status == 200 else 'FAIL'
    print(f'{icon} {status}  {path}  [{ct}]')

# Check branding in returned HTML
with urllib.request.urlopen(BASE + '/', timeout=5) as r:
    html = r.read().decode('utf-8', errors='replace')

branding_checks = [
    ('Dream Line Travels', 'title/footer branding'),
    ('DreamLine AI Agent', 'agent name'),
    ('dreamline-logo.png', 'logo reference'),
    ('Explore the World with DreamLine AI', 'hero heading'),
    ('POWERED BY DREAM LINE TRAVELS', 'hero label'),
    ('VoyageAI', 'OLD branding (should be ABSENT)'),
]

print()
print('--- HTML Branding Checks ---')
for token, desc in branding_checks:
    found = token in html
    if token == 'VoyageAI':
        status_str = 'ABSENT (good)' if not found else 'PRESENT (BAD!)'
        icon = 'OK ' if not found else 'FAIL'
    else:
        status_str = 'FOUND' if found else 'MISSING!'
        icon = 'OK ' if found else 'FAIL'
    print(f'{icon}  {desc}: {status_str}')

