import requests
import concurrent.futures

def issue_and_enforce(_):
    r = requests.post(
        'https://aion-protocol.onrender.com/issue',
        json={'scope': 'test.concurrent', 'issuer': 'agent'},
        headers={'X-AION-API-Key': 'aion-prod-key-2026'}
    )
    token = r.json()
    if 'jti' in token:
        e = requests.post(
            'https://aion-protocol.onrender.com/enforce',
            json={'jti': token['jti'], 'scope': 'test.concurrent'},
            headers={'X-AION-API-Key': 'aion-prod-key-2026'}
        )
        return e.json().get('status', 'DENIED')
    return 'FAILED'

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    results = list(ex.map(issue_and_enforce, range(50)))

print('ENFORCED:', results.count('ENFORCED'))
print('DENIED:', results.count('ENFORCEMENT_DENIED'))
print('FAILED:', results.count('FAILED'))
print('Total:', len(results))