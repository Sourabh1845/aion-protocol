"""AION x402 adapter - mandate enforcement for x402 agent payments.

x402 (Linux Foundation) moves money: HTTP 402 -> PAYMENT-REQUIRED ->
PAYMENT-SIGNATURE -> facilitator /verify -> /settle -> PAYMENT-RESPONSE.
x402's own principles require that funds only move "in accordance with client
intentions" - but the protocol has no way to express, sign, or prove those
intentions. That is the gap AION fills:

    PAYMENT-REQUIRED     <- what the seller asks for
    AION mandate check   <- is the BUYER allowed to pay this? (signed limits)
    AION payment auth    <- one-time, bound to these exact x402 terms
    facilitator /settle  <- money moves
    PAYMENT-RESPONSE     <- AION binds the settlement receipt into its chain

Three integration points:
    1. Client side   : authorize_x402()  before building PAYMENT-SIGNATURE
    2. Server side   : check_x402_against_mandate() inside /verify handlers
    3. Settlement    : settle_x402() to bind the on-chain receipt

Amounts are integers in the asset's smallest unit (same convention as AION).
x402 sends amounts as strings; they are parsed to int here.

Currency binding: for full cryptographic binding the mandate currency should be
the exact label returned by x402_currency_label() (e.g. "base:0x8335...2913"),
because AION binds (mandate_id, amount, payee, currency) into the signed auth.
A symbol match against requirements.extra.name is also accepted for convenience
and records currency_matched_by="symbol" in the decision.
"""

import base64
import binascii
import json
import logging
from datetime import datetime, timedelta, timezone

from aion.audit import log
from aion.payment_storage import get_mandate, get_payment_auth
from aion.payments import (
    CLOCK_SKEW_SECONDS,
    PAYMENT_AUTH_TTL_SECONDS,
    authorize_payment,
    settle_payment,
    verify_payment_auth,
)

logger = logging.getLogger(__name__)

PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"
PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"

# Legacy header names used by earlier x402 revisions.
LEGACY_ALIASES = {
    "X-PAYMENT": PAYMENT_SIGNATURE_HEADER,
    "X-PAYMENT-RESPONSE": PAYMENT_RESPONSE_HEADER,
}

DEFAULT_X402_VERSION = 1


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, default=str)


def encode_x402_header(payload):
    """Encode a dict as the base64 JSON value x402 expects in headers."""
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def decode_x402_header(header):
    """Decode a PAYMENT-* header value into a dict.

    Tolerates: base64-encoded JSON, raw JSON, or an already-parsed dict.
    Returns {"error": ...} when the input cannot be parsed.
    """
    if header is None:
        return {"error": "EMPTY_HEADER"}
    if isinstance(header, dict):
        return header
    if not isinstance(header, str) or not header.strip():
        return {"error": "EMPTY_HEADER"}

    text = header.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            return {"error": "MALFORMED_HEADER", "detail": str(exc)}

    try:
        decoded = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        try:
            decoded = base64.b64decode(text + "=" * (-len(text) % 4))
        except Exception as exc:
            return {"error": "MALFORMED_HEADER", "detail": str(exc)}

    try:
        return json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        return {"error": "MALFORMED_HEADER", "detail": str(exc)}


# ---- TERMS NORMALIZATION ----

def _parse_amount(value):
    """x402 sends amounts as strings in the asset's smallest unit (USDC 6dp)."""
    if isinstance(value, bool):
        return {"error": "INVALID_AMOUNT", "detail": "boolean is not an amount"}
    if isinstance(value, int):
        return {"amount": value}
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return {"amount": int(text)}
        return {
            "error": "INVALID_AMOUNT",
            "detail": f"amount must be an integer string in the smallest unit, got {value!r}",
        }
    return {
        "error": "INVALID_AMOUNT",
        "detail": f"unsupported amount type: {type(value).__name__}",
    }


def x402_currency_label(requirements):
    """Canonical AION currency label for an x402 asset: "<network>:<asset>"."""
    if not isinstance(requirements, dict):
        return None
    network = str(requirements.get("network") or "").strip()
    asset = str(requirements.get("asset") or "").strip()
    if network and asset:
        return f"{network}:{asset}"
    return network or asset or None


def x402_currency_symbol(requirements):
    """Asset symbol x402 exposes in extra.name (e.g. "USDC") when available."""
    if not isinstance(requirements, dict):
        return None
    extra = requirements.get("extra")
    if isinstance(extra, dict) and extra.get("name"):
        return str(extra["name"])
    return None


def select_requirements(payment_required, index=0):
    """Pick one PaymentRequirements out of a PAYMENT-REQUIRED envelope."""
    if isinstance(payment_required, str):
        payment_required = decode_x402_header(payment_required)
    if not isinstance(payment_required, dict):
        return {"error": "INVALID_REQUIREMENTS"}
    accepts = payment_required.get("accepts")
    if not isinstance(accepts, list) or not accepts:
        return {"error": "INVALID_REQUIREMENTS", "detail": "accepts[] missing or empty"}
    if index < 0 or index >= len(accepts):
        return {
            "error": "INVALID_REQUIREMENTS",
            "detail": f"accepts index {index} out of range ({len(accepts)} entries)",
        }
    selected = accepts[index]
    if not isinstance(selected, dict):
        return {"error": "INVALID_REQUIREMENTS", "detail": "accepts entry is not an object"}
    return selected


def x402_terms(requirements):
    """Normalize x402 PaymentRequirements into AION payment terms.

    Accepts a PaymentRequirements dict, a full PAYMENT-REQUIRED envelope
    (with accepts[]), or either of those as an encoded header string.
    """
    if isinstance(requirements, str):
        requirements = decode_x402_header(requirements)
    if not isinstance(requirements, dict):
        return {"error": "INVALID_REQUIREMENTS"}

    if set(requirements) <= {"error", "detail"}:
        return requirements

    if "accepts" in requirements:
        selected = select_requirements(requirements)
        if "error" in selected:
            return selected
        requirements = selected

    scheme = str(requirements.get("scheme") or "exact").lower().strip()
    payee = requirements.get("payTo") or requirements.get("pay_to")
    if not payee:
        return {"error": "INVALID_REQUIREMENTS", "detail": "payTo missing"}

    raw_amount = requirements.get("amount", requirements.get("maxAmountRequired"))
    parsed = _parse_amount(raw_amount)
    if "error" in parsed:
        return parsed

    return {
        "scheme": scheme,
        "network": str(requirements.get("network") or ""),
        "asset": str(requirements.get("asset") or ""),
        "currency": x402_currency_label(requirements),
        "symbol": x402_currency_symbol(requirements),
        "amount": parsed["amount"],
        "payee": str(payee),
        "resource": requirements.get("resource"),
        "description": requirements.get("description"),
        "timeout_seconds": requirements.get("maxTimeoutSeconds"),
        "raw": requirements,
    }


# ---- INTEGRATION POINT 1: CLIENT SIDE ----

def _resolve_currency(mandate, terms, override=None):
    """Match the mandate currency against the x402 asset label or its symbol.

    Returns (currency, matched_by) or (None, None) when neither matches.
    """
    label = terms.get("currency")
    symbol = terms.get("symbol")
    candidate = override or mandate.get("currency") or ""

    if label and candidate == label:
        return candidate, "asset"
    if symbol and candidate.upper() == symbol.upper():
        return candidate, "symbol"
    return None, None


def authorize_x402(mandate_id, requirements, agent=None, amount=None, currency=None, ttl_seconds=None):
    """Authorize an x402 payment against an AION mandate before signing it.

    Call this BEFORE building the PAYMENT-SIGNATURE payload. On allow you get a
    one-time AION auth bound to the exact x402 terms; the returned aion_jti is
    what the seller/facilitator verifies at integration point 2.
    """
    terms = x402_terms(requirements)
    if "error" in terms:
        return {"decision": "block", "reason": terms["error"], "detail": terms.get("detail")}

    mandate = get_mandate(mandate_id)
    if not mandate:
        return {"decision": "block", "reason": "MANDATE_NOT_FOUND", "detail": mandate_id}

    scheme = terms["scheme"]
    if scheme not in {"exact", "upto"}:
        return {
            "decision": "block",
            "reason": "UNSUPPORTED_SCHEME",
            "detail": f"scheme {scheme!r} not supported by the AION x402 adapter",
        }

    spend = terms["amount"] if amount is None else amount
    if not isinstance(spend, int) or spend <= 0:
        return {
            "decision": "block",
            "reason": "INVALID_AMOUNT",
            "detail": "amount must be a positive int in the asset's smallest unit",
        }
    if spend > terms["amount"]:
        return {
            "decision": "block",
            "reason": "AMOUNT_LIMIT",
            "detail": f"{spend} exceeds the x402 request cap {terms['amount']}",
        }
    if scheme == "exact" and spend != terms["amount"]:
        return {
            "decision": "block",
            "reason": "AMOUNT_MISMATCH",
            "detail": f"exact scheme requires the full {terms['amount']}, got {spend}",
        }

    resolved_currency, matched_by = _resolve_currency(mandate, terms, currency)
    if resolved_currency is None:
        return {
            "decision": "block",
            "reason": "CURRENCY_MISMATCH",
            "detail": (
                f"mandate currency {mandate.get('currency')!r} matches neither asset "
                f"{terms.get('currency')!r} nor symbol {terms.get('symbol')!r}"
            ),
        }

    auth = authorize_payment(
        mandate_id=mandate_id,
        agent=agent or mandate["agent"],
        amount=spend,
        payee=terms["payee"],
        currency=resolved_currency,
        ttl_seconds=ttl_seconds or PAYMENT_AUTH_TTL_SECONDS,
    )
    if "error" in auth:
        return {"decision": "block", "reason": auth["error"], "detail": auth.get("detail")}

    log("X402_AUTHORIZE", {
        "jti": auth["jti"],
        "mandate_id": mandate_id,
        "network": terms["network"],
        "asset": terms["asset"],
        "amount": spend,
    })
    logger.info(f"x402 payment authorized: {auth['jti']} {spend} -> {terms['payee']}")
    return {
        "decision": "allow",
        "aion_jti": auth["jti"],
        "mandate_id": mandate_id,
        "amount": spend,
        "payee": terms["payee"],
        "currency": resolved_currency,
        "x402": {
            "scheme": scheme,
            "network": terms["network"],
            "asset": terms["asset"],
            "resource": terms["resource"],
            "currency_matched_by": matched_by,
        },
        "auth": auth,
    }


# ---- DECISION HELPERS ----

def _deny(reason, detail=None):
    return {"decision": "block", "reason": reason, "detail": detail}


def _settlement_ref(payment_response):
    """Pull the transaction hash out of an x402 SettlementResponse.

    x402 names it `transaction`; facilitators in the wild also emit txHash,
    transactionHash or tx_hash. First non-empty wins.
    """
    for key in ("transaction", "txHash", "transactionHash", "tx_hash", "settlementRef"):
        value = payment_response.get(key)
        if value:
            return str(value)
    return None


# ---- INTEGRATION POINT 2: SERVER SIDE ----

def check_x402_against_mandate(mandate_id, requirements, aion_jti):
    """Seller/facilitator side: does this AION auth cover these exact x402 terms?

    Read-only. Buyer's signed limits are re-checked here, so a seller never has
    to trust the client's claim that the payment was permitted.
    """
    terms = x402_terms(requirements)
    if "error" in terms:
        return _deny(terms["error"], terms.get("detail"))

    if not aion_jti:
        return _deny("AION_AUTH_MISSING", "no aion_jti presented with the payment")

    check = verify_payment_auth(aion_jti)
    if "error" in check:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "mandate_id": mandate_id, "reason": check["error"]})
        return _deny(check["error"], check.get("detail"))

    if check["mandate_id"] != mandate_id:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "MANDATE_MISMATCH"})
        return _deny(
            "MANDATE_MISMATCH",
            f"auth belongs to mandate {check['mandate_id']}, not {mandate_id}",
        )
    if not check["signature_valid"]:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "INVALID_SIGNATURE"})
        return _deny("INVALID_SIGNATURE", "auth terms were tampered after authorization")
    if not check["binding_valid"]:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "BINDING_MISMATCH"})
        return _deny("BINDING_MISMATCH", "amount/payee/currency no longer match the signed binding")
    if check["payment_status"] == "SETTLED":
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "AUTH_ALREADY_SETTLED"})
        return _deny("AUTH_ALREADY_SETTLED", "this auth was already settled (replay blocked)")
    if check["payment_status"] != "AUTHORIZED":
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "AUTH_NOT_ACTIVE"})
        return _deny("AUTH_NOT_ACTIVE", f"auth status is {check['payment_status']}")

    stored = get_payment_auth(aion_jti)
    if stored and stored.get("expires_at"):
        expires_at = datetime.fromisoformat(stored["expires_at"])
        if expires_at + timedelta(seconds=CLOCK_SKEW_SECONDS) < datetime.now(timezone.utc):
            log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "AUTH_EXPIRED"})
            return _deny("AUTH_EXPIRED", f"auth expired at {stored['expires_at']}")

    if check["payee"] != terms["payee"]:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "PAYEE_MISMATCH"})
        return _deny("PAYEE_MISMATCH", f"auth pays {check['payee']}, request wants {terms['payee']}")

    if terms["scheme"] == "exact" and check["amount"] != terms["amount"]:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "AMOUNT_MISMATCH"})
        return _deny("AMOUNT_MISMATCH", f"auth authorizes {check['amount']}, request wants {terms['amount']}")
    if check["amount"] > terms["amount"]:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "AMOUNT_LIMIT"})
        return _deny("AMOUNT_LIMIT", f"auth authorizes {check['amount']}, above the request cap {terms['amount']}")

    matched_currency, matched_by = _resolve_currency({"currency": check["currency"]}, terms)
    if matched_currency is None:
        log("X402_CHECK_FAIL", {"jti": aion_jti, "reason": "CURRENCY_MISMATCH"})
        return _deny(
            "CURRENCY_MISMATCH",
            f"auth currency {check['currency']!r} matches neither asset {terms.get('currency')!r} nor symbol {terms.get('symbol')!r}",
        )

    log("X402_CHECK_OK", {
        "jti": aion_jti,
        "mandate_id": mandate_id,
        "amount": check["amount"],
        "network": terms["network"],
    })
    # Read-only envelope: the buyer's signed limits were re-checked above, so a
    # seller never has to trust the client's claim that the payment was allowed.
    return {
        "decision": "allow",
        "aion_jti": aion_jti,
        "mandate_id": mandate_id,
        "amount": check["amount"],
        "payee": check["payee"],
        "currency": check["currency"],
        "currency_matched_by": matched_by,
        "payment_status": check["payment_status"],
        "x402": {
            "scheme": terms["scheme"],
            "network": terms["network"],
            "asset": terms["asset"],
            "resource": terms["resource"],
        },
    }


# ---- INTEGRATION POINT 3: SETTLEMENT ----

def settle_x402(aion_jti, payment_response):
    """Bind an x402 settlement (PAYMENT-RESPONSE) into the AION receipt chain.

    `payment_response` is the decoded PAYMENT-RESPONSE header (or the encoded
    string) returned by the facilitator after /settle. Its transaction hash
    becomes the AION settlement reference, so the dispute bundle carries
    on-chain proof instead of just the operator's word.

    Replay is blocked downstream: an auth that is already SETTLED is rejected by
    settle_payment(), which makes a second x402 settle call fail loudly.
    """
    if isinstance(payment_response, str):
        payment_response = decode_x402_header(payment_response)
    if not isinstance(payment_response, dict):
        return _deny("INVALID_SETTLEMENT_RESPONSE", "expected an object or encoded header")

    if set(payment_response) <= {"error", "detail"}:
        return _deny(payment_response["error"], payment_response.get("detail"))

    # x402 facilitators report the outcome in `success`; false means no money
    # moved, so there is nothing to bind.
    if payment_response.get("success") is False:
        return _deny("SETTLEMENT_FAILED", "facilitator reported success=false")

    settlement_ref = _settlement_ref(payment_response)
    if not settlement_ref:
        return _deny(
            "SETTLEMENT_REF_MISSING",
            "PAYMENT-RESPONSE carries no transaction hash to bind",
        )

    result = settle_payment(aion_jti, settlement_ref)
    if "error" in result:
        log("X402_SETTLE_FAIL", {"jti": aion_jti, "reason": result["error"]})
        return _deny(result["error"], result.get("detail"))

    log("X402_SETTLE", {
        "jti": aion_jti,
        "settlement_ref": settlement_ref,
        "network": payment_response.get("network"),
        "payer": payment_response.get("payer"),
    })
    logger.info(f"x402 settlement bound: {aion_jti} tx: {settlement_ref}")
    return {
        "decision": "settled",
        "aion_jti": aion_jti,
        "settlement_ref": settlement_ref,
        "receipt_hash": result.get("receipt_hash"),
        "network": payment_response.get("network"),
        "payer": payment_response.get("payer"),
    }


# ---- CONVENIENCE ----

def extract_aion_jti(payment_payload):
    """Read the AION auth id a client attached to an x402 PAYMENT-SIGNATURE.

    Accepts the decoded payload, an encoded header string, or a `payload` dict.
    Clients carry it either at the top level (aionJti) or inside payload.
    """
    if isinstance(payment_payload, str):
        payment_payload = decode_x402_header(payment_payload)
    if not isinstance(payment_payload, dict):
        return None

    for key in ("aionJti", "aion_jti", "aionAuth"):
        if payment_payload.get(key):
            return str(payment_payload[key])

    inner = payment_payload.get("payload")
    if isinstance(inner, dict):
        for key in ("aionJti", "aion_jti", "aionAuth"):
            if inner.get(key):
                return str(inner[key])
    return None


def build_payment_signature(payment_payload, aion_jti):
    """Attach an AION auth id to an x402 payload and encode it as a header.

    Use the result as the value of the PAYMENT-SIGNATURE header.
    """
    if not isinstance(payment_payload, dict):
        return {"error": "INVALID_PAYLOAD", "detail": "payment payload must be an object"}
    if not aion_jti:
        return {"error": "AION_AUTH_MISSING", "detail": "aion_jti is required"}

    enriched = dict(payment_payload)
    enriched["aionJti"] = aion_jti
    return {"header": PAYMENT_SIGNATURE_HEADER, "value": encode_x402_header(enriched)}