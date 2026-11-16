import os

content = open('frontend/index.html', encoding='utf-8').read()
checks = [
    ('Dream Line Travels',               'Company name',       False),
    ('DreamLine AI Agent',               'Agent name',         False),
    ('dreamline-logo.png',               'Logo reference',     False),
    ('Explore the World with DreamLine AI', 'Hero heading',    False),
    ('POWERED BY DREAM LINE TRAVELS',    'Hero label',         False),
    ('Your Intelligent Travel Companion','Title tagline',      False),
    ('2026 Dream Line Travels',          'Footer copyright',   False),
    ('VoyageAI',                         'OLD branding',       True),
]

print('--- index.html branding checks ---')
all_ok = True
for token, desc, should_be_absent in checks:
    found = token in content
    if should_be_absent:
        ok = not found
        status = 'ABSENT (good)' if ok else 'PRESENT (BAD!)'
    else:
        ok = found
        status = 'FOUND' if found else 'MISSING!'
    icon = 'OK ' if ok else 'FAIL'
    if not ok:
        all_ok = False
    print('  ' + icon + '  ' + desc + ': ' + status)

css = open('frontend/css/styles.css', encoding='utf-8').read()
css_checks = [
    ('#35B7BD', 'Teal primary color'),
    ('#B12585', 'Magenta secondary'),
    ('#12172E', 'Navy background'),
    ('#8DE0E3', 'Cyan accent'),
    ('brand-logo', 'Logo CSS class'),
    ('@media', 'Responsive media queries'),
]
print()
print('--- styles.css brand color checks ---')
for token, desc in css_checks:
    found = token in css
    icon = 'OK ' if found else 'FAIL'
    if not found:
        all_ok = False
    print('  ' + icon + '  ' + desc + ': ' + ('FOUND' if found else 'MISSING!'))

logo_path = os.path.join('frontend', 'assets', 'dreamline-logo.png')
logo_exists = os.path.isfile(logo_path)
logo_size = os.path.getsize(logo_path) if logo_exists else 0
print()
icon = 'OK ' if logo_exists else 'FAIL'
print('  ' + icon + '  Logo file: ' + ('EXISTS' if logo_exists else 'MISSING') + ' (' + str(logo_size) + ' bytes)')

print()
print('OVERALL: ' + ('ALL CHECKS PASSED' if (all_ok and logo_exists) else 'SOME CHECKS FAILED'))

