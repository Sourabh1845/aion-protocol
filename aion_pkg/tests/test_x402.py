import sqlite3
from pathlib import Path

from aion.payments import create_intent_mandate
from aion.payment_storage import get_payment_auth
from aion.x402 import (
    authorize_x402,
    build_payment_signature,
    check_x402_against_mandate,
    decode_x402_header,
    encode_x402_header,
    extract_aion_jti,
    settle_x402,
    x402_currency_label,
    x402_terms,
)

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"

# Base mainnet USDC — the asset x402 puts in PaymentRequirements.asset
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54BdA2913"
PAYEE = "merchant:api.example.com"


def _db():
    return sqlite3.connect(str(DB_FILE))


def _mandate(payees=None, **overrides):
    defaults = dict(
        principal="user:alice",
        agent="agent:shopper",
        max_per_payment=5000000,
        max_total=10000000,
        currency=f"base:{USDC}",
        payees=payees if payees is not None else [PAYEE],
    )
    defaults.update(overrides)
    return create_intent_mandate(**defaults)


def _requirements(**overrides):
    payload = {
        "scheme": "exact",
        "network": "base",
        "asset": USDC,
        "amount": "3000000",
        "payTo": PAYEE,
        "resource": "https://api.example.com/premium",
        "extra": {"name": "USDC"},
    }
    payload.update(overrides)
    return payload


def _settlement_response(**overrides):
    payload = {
        "success": True,
        "transaction": "0xabc123def456",
        "network": "base",
        "payer": "0xpayer",
    }
    payload.update(overrides)
    return payload


def test_x402_full_flow():
    mandate = _mandate()
    terms = x402_terms(_requirements())
    assert "error" not in terms, terms
    assert terms["amount"] == 3000000
    assert terms["payee"] == PAYEE
    assert terms["currency"] == f"base:{USDC}"

    # Client side: authorize before building PAYMENT-SIGNATURE
    decision = authorize_x402(mandate["mandate_id"], _requirements())
    assert decision["decision"] == "allow", decision
    jti = decision["aion_jti"]
    assert decision["amount"] == 3000000

    # Attach the AION auth to the x402 payload
    signed = build_payment_signature({"x402Version": 1, "scheme": "exact"}, jti)
    assert signed["header"] == "PAYMENT-SIGNATURE"
    assert extract_aion_jti(signed["value"]) == jti

    # Server side: seller re-verifies against the buyer's signed limits
    check = check_x402_against_mandate(mandate["mandate_id"], _requirements(), jti)
    assert check["decision"] == "allow", check
    assert check["currency_matched_by"] == "asset"
    assert check["payment_status"] == "AUTHORIZED"

    # Settlement: bind the on-chain tx hash into the AION chain
    settled = settle_x402(jti, _settlement_response())
    assert settled["decision"] == "settled", settled
    assert settled["settlement_ref"] == "0xabc123def456"
    assert settled["receipt_hash"]

    stored = get_payment_auth(jti)
    assert stored["status"] == "SETTLED"
    assert stored["settlement_ref"] == "0xabc123def456"
    print("x402 full flow test PASSED")


def test_x402_symbol_match():
    # Mandate says "USDC", x402 asset is the contract address -> symbol match
    mandate = _mandate(currency="USDC")
    decision = authorize_x402(mandate["mandate_id"], _requirements())
    assert decision["decision"] == "allow", decision
    assert decision["currency"] == "USDC"
    assert decision["x402"]["currency_matched_by"] == "symbol"
    print("x402 symbol match test PASSED")


def test_x402_currency_mismatch_blocked():
    mandate = _mandate(currency="EURC")  # neither asset nor symbol matches
    decision = authorize_x402(mandate["mandate_id"], _requirements())
    assert decision["decision"] == "block"
    assert decision["reason"] == "CURRENCY_MISMATCH"
    print("x402 currency mismatch test PASSED")


def test_x402_payee_not_allowed():
    mandate = _mandate()
    decision = authorize_x402(
        mandate["mandate_id"], _requirements(payTo="merchant:sketchy.io")
    )
    assert decision["decision"] == "block"
    assert decision["reason"] == "PAYEE_NOT_ALLOWED"
    print("x402 payee allowlist test PASSED")


def test_x402_unsupported_scheme():
    mandate = _mandate()
    decision = authorize_x402(
        mandate["mandate_id"], _requirements(scheme="batch-settlement")
    )

def test_x402_upto_scheme():
    mandate = _mandate()

    # upto: seller settles the actual amount, capped by maxAmountRequired
    decision = authorize_x402(
        mandate["mandate_id"], _requirements(scheme="upto"), amount=1500000
    )
    assert decision["decision"] == "allow", decision
    assert decision["amount"] == 1500000

    # Actual above the x402 request cap is refused
    over = authorize_x402(
        mandate["mandate_id"], _requirements(scheme="upto"), amount=4000000
    )
    assert over["decision"] == "block"
    assert over["reason"] == "AMOUNT_LIMIT"
    print("x402 upto scheme test PASSED")


def test_x402_exact_partial_blocked():
    mandate = _mandate()
    decision = authorize_x402(
        mandate["mandate_id"], _requirements(scheme="exact"), amount=2000000
    )
    assert decision["decision"] == "block"
    assert decision["reason"] == "AMOUNT_MISMATCH"
    print("x402 exact partial amount test PASSED")


def test_x402_mandate_budget_still_applies():
    # x402 terms fit, but the AION mandate budget does not -> mandate wins
    mandate = _mandate(max_per_payment=1000000, max_total=1000000)
    decision = authorize_x402(mandate["mandate_id"], _requirements())
    assert decision["decision"] == "block"
    assert decision["reason"] == "AMOUNT_LIMIT"
    print("x402 mandate budget test PASSED")


def test_x402_envelope_with_accepts():
    envelope = {"x402Version": 1, "accepts": [_requirements()]}
    terms = x402_terms(envelope)
    assert "error" not in terms, terms
    assert terms["amount"] == 3000000

    # Missing accepts[] is a malformed envelope, not a crash
    bad = x402_terms({"x402Version": 1})
    assert bad["error"] == "INVALID_REQUIREMENTS"
    print("x402 envelope test PASSED")


def test_x402_header_roundtrip():
    encoded = encode_x402_header(_requirements())
    assert isinstance(encoded, str)
    decoded = decode_x402_header(encoded)
    assert decoded["payTo"] == PAYEE

    # Raw JSON is tolerated too (some clients skip base64)
    raw = decode_x402_header('{"scheme": "exact"}')
    assert raw["scheme"] == "exact"

    assert decode_x402_header(None)["error"] == "EMPTY_HEADER"
    assert decode_x402_header("!!!not-base64!!!")["error"] == "MALFORMED_HEADER"
    print("x402 header roundtrip test PASSED")


def test_x402_currency_label():
    label = x402_currency_label(_requirements())
    assert label == f"base:{USDC}"
    assert x402_currency_label({"network": "base"}) == "base"
    assert x402_currency_label("not-a-dict") is None
    print("x402 currency label test PASSED")

