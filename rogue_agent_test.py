import requests
import time
import json
from datetime import datetime

AION_BASE_URL = "https://aion-protocol.onrender.com"
AION_API_KEY = "aion-prod-key-2026"
FAKE_API_KEY = "hacker-fake-key-xyz"

headers_valid = {"X-AION-API-Key": AION_API_KEY, "Content-Type": "application/json"}
headers_fake = {"X-AION-API-Key": FAKE_API_KEY, "Content-Type": "application/json"}

results = []

def log(test_name, expected, actual, passed):
    status = "PASS" if passed else "FAIL"
    results.append({
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "status": status
    })
    print(f"  [{status}] {test_name}")
    print(f"         Expected : {expected}")
    print(f"         Got      : {actual}")
    print()

def run_tests():
    print("\n" + "="*65)
    print("  AION PROTOCOL — ROGUE AGENT SECURITY TEST SUITE")
    print("  Simulating real-world adversarial agent behavior")
    print("="*65 + "\n")

    # ─────────────────────────────────────────────
    # BLOCK 1: Authentication Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 1: Authentication Attacks ──────────────────────────\n")

    # Test 1.1 — No API key
    r = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "read.data", "issuer": "rogue-agent"},
        headers={"Content-Type": "application/json"})
    passed = r.status_code == 401 or "error" in r.json() or "detail" in r.json()
    log("1.1 Issue token with NO API key",
        "401 Unauthorized", f"HTTP {r.status_code} — {r.json()}", passed)

    # Test 1.2 — Fake API key
    r = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "read.data", "issuer": "rogue-agent"},
        headers=headers_fake)
    passed = r.status_code == 401 or "error" in r.json() or "detail" in r.json()
    log("1.2 Issue token with FAKE API key",
        "401 Unauthorized", f"HTTP {r.status_code} — {r.json()}", passed)

    # ─────────────────────────────────────────────
    # BLOCK 2: Token Forgery Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 2: Token Forgery Attacks ───────────────────────────\n")

    # Test 2.1 — Completely fake JTI
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": "00000000-0000-0000-0000-000000000000", "scope": "read.data"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("2.1 Enforce with completely fake JTI",
        "NOT_FOUND or error", str(r.json()), passed)

    # Test 2.2 — Tampered JTI (1 char changed)
    real_token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "read.data", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    jti = real_token.get("jti", "")
    tampered_jti = "a" + jti[1:] if jti else "invalid"
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": tampered_jti, "scope": "read.data"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("2.2 Enforce with TAMPERED JTI (1 char changed)",
        "NOT_FOUND or error", str(r.json()), passed)

    # Test 2.3 — SQL injection in JTI
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": "' OR '1'='1", "scope": "read.data"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("2.3 SQL injection attempt in JTI field",
        "error / blocked", str(r.json()), passed)

    # ─────────────────────────────────────────────
    # BLOCK 3: Scope Escalation Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 3: Scope Escalation Attacks ────────────────────────\n")

    # Test 3.1 — Agent tries higher scope than issued
    token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "read.data", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": token["jti"], "scope": "delete.database"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("3.1 Scope escalation: read.data token used for delete.database",
        "SCOPE_MISMATCH", str(r.json()), passed)

    # Test 3.2 — Agent tries admin scope
    token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "read.files", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": token["jti"], "scope": "admin.root.access"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("3.2 Scope escalation: read.files token used for admin.root.access",
        "SCOPE_MISMATCH", str(r.json()), passed)

    # ─────────────────────────────────────────────
    # BLOCK 4: Replay Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 4: Replay Attacks ───────────────────────────────────\n")

    # Test 4.1 — Same token used twice
    token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "send.email", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    jti = token["jti"]
    r1 = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": jti, "scope": "send.email"},
        headers=headers_valid)
    r2 = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": jti, "scope": "send.email"},
        headers=headers_valid)
    passed = r1.json().get("status") == "ENFORCED" and "error" in r2.json()
    log("4.1 Replay attack: same token used twice",
        "1st=ENFORCED, 2nd=CONSUMED", f"1st={r1.json()} 2nd={r2.json()}", passed)

    # Test 4.2 — 5 rapid replay attempts
    token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "write.file", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    jti = token["jti"]
    responses = []
    for _ in range(5):
        r = requests.post(f"{AION_BASE_URL}/enforce",
            json={"jti": jti, "scope": "write.file"},
            headers=headers_valid)
        responses.append(r.json().get("status", r.json().get("reason", "error")))
    enforced = responses.count("ENFORCED")
    passed = enforced == 1
    log("4.2 5 rapid replay attempts on same token",
        "Exactly 1 ENFORCED, rest blocked", str(responses), passed)

    # ─────────────────────────────────────────────
    # BLOCK 5: Revocation Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 5: Revocation Attacks ───────────────────────────────\n")

    # Test 5.1 — Use token after revocation
    token = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "delete.file", "issuer": "rogue-agent"},
        headers=headers_valid).json()
    jti = token["jti"]
    requests.post(f"{AION_BASE_URL}/revoke/{jti}", headers=headers_valid)
    r = requests.post(f"{AION_BASE_URL}/enforce",
        json={"jti": jti, "scope": "delete.file"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("5.1 Enforce after revocation",
        "REVOKED", str(r.json()), passed)

    # ─────────────────────────────────────────────
    # BLOCK 6: Edge Case Attacks
    # ─────────────────────────────────────────────
    print("── BLOCK 6: Edge Case Attacks ────────────────────────────────\n")

    # Test 6.1 — Empty scope
    r = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "", "issuer": "rogue-agent"},
        headers=headers_valid)
    passed = "error" in r.json()
    log("6.1 Issue token with EMPTY scope",
        "INVALID_SCOPE or error", str(r.json()), passed)

    # Test 6.2 — Extremely long scope
    long_scope = "a" * 10000
    r = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": long_scope, "issuer": "rogue-agent"},
        headers=headers_valid)
    passed = r.status_code in [400, 422] or "error" in r.json()
    log("6.2 Issue token with 10,000 character scope",
        "error or 422", f"HTTP {r.status_code} — {str(r.json())[:100]}", passed)

    # Test 6.3 — Special characters in scope
    r = requests.post(f"{AION_BASE_URL}/issue",
        json={"scope": "<script>alert('xss')</script>", "issuer": "rogue-agent"},
        headers=headers_valid)
    passed = "error" in r.json() or r.status_code in [400, 422]
    log("6.3 XSS attempt in scope field",
        "error or blocked", f"HTTP {r.status_code} — {str(r.json())[:100]}", passed)

    # ─────────────────────────────────────────────
    # FINAL REPORT
    # ─────────────────────────────────────────────
    print("="*65)
    print("  FINAL REPORT")
    print("="*65)
    total = len(results)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    failed = [r for r in results if r["status"] == "FAIL"]

    print(f"\n  Total Tests  : {total}")
    print(f"  Passed       : {passed_count}")
    print(f"  Failed       : {total - passed_count}")
    print(f"  Score        : {passed_count}/{total}")

    if failed:
        print("\n  ── Failed Tests ──")
        for f in failed:
            print(f"  ✗ {f['test']}")
            print(f"    Expected : {f['expected']}")
            print(f"    Got      : {f['actual']}")
    else:
        print("\n  ✓ All tests passed — AION blocked every attack vector.")

    print("\n" + "="*65 + "\n")

run_tests()