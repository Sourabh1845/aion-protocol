import os

import requests

BASE_URL = os.getenv("AION_BASE_URL", "https://aion-protocol.onrender.com")
API_KEY = os.getenv("AION_API_KEY")

if not API_KEY:
    raise SystemExit(
        "AION_API_KEY is not set. Set it first, e.g.  set AION_API_KEY=<your-key>"
    )

h = {"X-AION-API-Key": API_KEY, "Content-Type": "application/json"}
t = requests.post(f"{BASE_URL}/issue", json={"scope": "read.data", "issuer": "test"}, headers=h).json()
jti = t["jti"]
tampered = "zzz-invalid-" + jti[12:]
r = requests.post(f"{BASE_URL}/enforce", json={"jti": tampered, "scope": "read.data"}, headers=h)
print('Original JTI:', jti)
print('Tampered JTI:', tampered)
print('Result:', r.json())