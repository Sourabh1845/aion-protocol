import os
import concurrent.futures

import requests

BASE_URL = os.getenv("AION_BASE_URL", "https://aion-protocol.onrender.com")
API_KEY = os.getenv("AION_API_KEY")

if not API_KEY:
    raise SystemExit(
        "AION_API_KEY is not set. Set it first, e.g.  set AION_API_KEY=<your-key>"
    )

HEADERS = {"X-AION-API-Key": API_KEY, "Content-Type": "application/json"}


def issue_and_enforce(_):
    r = requests.post(
        f'{BASE_URL}/issue',
        json={'scope': 'test.concurrent', 'issuer': 'agent'},
        headers=HEADERS
    )
    token = r.json()
    if 'jti' in token:
        e = requests.post(
            f'{BASE_URL}/enforce',
            json={'jti': token['jti'], 'scope': 'test.concurrent'},
            headers=HEADERS
        )
        return e.json().get('status', 'DENIED')
    return 'FAILED'

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    results = list(ex.map(issue_and_enforce, range(50)))

print('ENFORCED:', results.count('ENFORCED'))
print('DENIED:', results.count('ENFORCEMENT_DENIED'))
print('FAILED:', results.count('FAILED'))
print('Total:', len(results))