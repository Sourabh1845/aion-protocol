import json
import sqlite3
from pathlib import Path

from aion.payments import (
    authorize_payment,
    create_intent_mandate,
    export_dispute_bundle,
    settle_payment,
    verify_payment_auth,
    verify_payment_chain,
)
from aion.payment_storage import get_payment_auth

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"


def _db():
    return sqlite3.connect(str(DB_FILE))


def _mandate(**overrides):
    defaults = dict(
        principal="user:alice",
        agent="agent:shopbot",
        max_per_payment=500,
        max_total=1000,
        payees=["api:weather", "api:news"],
    )
    defaults.update(overrides)
    return create_intent_mandate(**defaults)


def test_payment_lifecycle():
    mandate = _mandate()
    assert "error" not in mandate
    assert mandate["signature"]
    assert mandate["spent"] == 0

    # Agent ne payment maanga — authorize hona chahiye
    auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 300, "api:weather")
    assert "error" not in auth, auth
    assert auth["status"] == "AUTHORIZED"
    assert auth["binding_hash"]

    # Mandate spend track ho gaya
    m = json.loads(json.dumps(mandate))  # noop, keep style
    from aion.payment_storage import get_mandate
    fresh = get_mandate(mandate["mandate_id"])
    assert fresh["spent"] == 300
    assert fresh["payments_count"] == 1

    # Settlement — proof attach hona chahiye
    result = settle_payment(auth["jti"], "x402:tx_0xabc123")
    assert result["status"] == "SETTLED", result
    assert result["receipt_hash"]

    settled = get_payment_auth(auth["jti"])
    assert settled["status"] == "SETTLED"
    assert settled["settlement_ref"] == "x402:tx_0xabc123"

    # Third-party read-only verify
    check = verify_payment_auth(auth["jti"])
    assert check["signature_valid"] is True
    assert check["binding_valid"] is True
    assert check["payment_status"] == "SETTLED"
    print("Payment lifecycle test PASSED")


def test_replay_settlement_blocked():
    mandate = _mandate()
    auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 100, "api:news")
    first = settle_payment(auth["jti"], "x402:tx_1")
    assert first["status"] == "SETTLED"

    # Doosri baar same auth settle karna — block hona chahiye (double-spend)
    replay = settle_payment(auth["jti"], "x402:tx_2")
    assert replay["error"] == "ALREADY_SETTLED"
    print("Replay settlement test PASSED")


def test_payee_allowlist():
    mandate = _mandate()
    result = authorize_payment(
        mandate["mandate_id"], "agent:shopbot", 100, "api:sketchy-shop"
    )
    assert result["error"] == "PAYEE_NOT_ALLOWED"
    print("Payee allowlist test PASSED")


def test_per_payment_limit():
    mandate = _mandate()  # max_per_payment=500
    result = authorize_payment(
        mandate["mandate_id"], "agent:shopbot", 900, "api:weather"
    )
    assert result["error"] == "AMOUNT_LIMIT"
    print("Per-payment limit test PASSED")


def test_budget_exhausted():
    mandate = _mandate()  # max_total=1000
    a1 = authorize_payment(mandate["mandate_id"], "agent:shopbot", 400, "api:weather")
    a2 = authorize_payment(mandate["mandate_id"], "agent:shopbot", 400, "api:news")
    assert "error" not in a1
    assert "error" not in a2

    # Total 800 ho gaya — ab 300 aur nahi chalega
    a3 = authorize_payment(mandate["mandate_id"], "agent:shopbot", 300, "api:weather")
    assert a3["error"] == "BUDGET_EXHAUSTED"

    # Lekin budget ke andar 200 chalega
    a4 = authorize_payment(mandate["mandate_id"], "agent:shopbot", 200, "api:weather")
    assert "error" not in a4
    print("Budget exhaustion test PASSED")


def test_agent_mismatch():
    mandate = _mandate()
    result = authorize_payment(
        mandate["mandate_id"], "agent:rogue", 100, "api:weather"
    )
    assert result["error"] == "AGENT_MISMATCH"
    print("Agent mismatch test PASSED")


def test_tampered_terms_detected():
    mandate = _mandate()
    auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 100, "api:weather")
    assert "error" not in auth

    # Attacker DB mein amount badal deta hai 100 -> 10000
    conn = _db()
    conn.execute(
        "UPDATE payment_auths SET amount=10000 WHERE jti=?", (auth["jti"],)
    )
    conn.commit()
    conn.close()

    # Settlement pe binding mismatch pakda jana chahiye
    result = settle_payment(auth["jti"], "x402:tx_hack")
    assert result["error"] == "BINDING_MISMATCH"

    # Chain bhi tootna chahiye
    assert verify_payment_chain(mandate["mandate_id"]) is False
    print("Tamper detection test PASSED")


def test_chain_verification_intact():
    mandate = _mandate(max_per_payment=200, max_total=600)
    for payee in ("api:weather", "api:news", "api:weather"):
        auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 200, payee)
        assert "error" not in auth

    # Sab payments chain mein linked hain — chain intact honi chahiye
    assert verify_payment_chain(mandate["mandate_id"]) is True
    print("Chain integrity test PASSED")


def test_dispute_bundle():
    mandate = _mandate()
    a1 = authorize_payment(mandate["mandate_id"], "agent:shopbot", 250, "api:weather")
    settle_payment(a1["jti"], "x402:tx_ok")
    authorize_payment(mandate["mandate_id"], "agent:shopbot", 250, "api:news")

    bundle = export_dispute_bundle(mandate["mandate_id"])
    assert bundle["bundle_type"] == "AION_DISPUTE_BUNDLE"
    assert bundle["chain_intact"] is True
    assert bundle["total_authorized"] == 500
    assert bundle["total_settled"] == 250
    assert bundle["bundle_hash"]
    assert all(p["signature_valid"] and p["binding_valid"] for p in bundle["payments"])
    print("Dispute bundle test PASSED")
