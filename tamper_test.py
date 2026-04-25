import requests

h = {'X-AION-API-Key': 'aion-prod-key-2026', 'Content-Type': 'application/json'}
t = requests.post('https://aion-protocol.onrender.com/issue', json={'scope': 'read.data', 'issuer': 'test'}, headers=h).json()
jti = t['jti']
tampered = 'zzz-invalid-' + jti[12:]
r = requests.post('https://aion-protocol.onrender.com/enforce', json={'jti': tampered, 'scope': 'read.data'}, headers=h)
print('Original JTI:', jti)
print('Tampered JTI:', tampered)
print('Result:', r.json())