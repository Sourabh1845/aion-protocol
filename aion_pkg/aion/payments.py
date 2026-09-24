"""AION Payment Rails - cryptographic trust layer for agent payments.

Flow:
    1. Principal creates a signed Intent Mandate (budget + limits + payees)
    2. Agent requests a one-time Payment Auth bound to exact amount + payee
    3. Payment settles - settlement evidence is attached to the auth
    4. Every auth is hash-chained; dispute bundles are third-party verifiable

Attack table:
    Fake auth              -> AUTH_NOT_FOUND
    Auth replay            -> AUTH_CONSUMED / ALREADY_SETTLED
    Amount swap            -> INVALID_SIGNATURE (terms tamper detected)
    Payee swap             -> PAYEE_NOT_ALLOWED
    Over per-payment limit -> AMOUNT_LIMIT
    Over total budget      -> BUDGET_EXHAUSTED
    Expired mandate/auth   -> MANDATE_EXPIRED / AUTH_EXPIRED
    Tampered ledger row    -> chain verification fails
"""

import base64
import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from aion.audit import log
from aion.payment_storage import (
    get_mandate,
    get_payment_auth,
    increment_mandate_spend,
    list_payment_auths,
    save_mandate,
    save_payment_auth,
    set_mandate_revoked,
    update_payment_auth,
)
from aion.receipts import record_receipt
from aion.token_signing import load_keys

logger = logging.getLogger(__name__)

PAYMENT_AUTH_TTL_SECONDS = 120
CLOCK_SKEW_SECONDS = 30  # money-grade clock tolerance (matches core option A)
DEFAULT_SCOPE = "payment.spend"

_key_cache = None


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, default=str)


def _get_keys():
    global _key_cache
    if _key_cache is None:
        _key_cache = load_keys()
    return _key_cache


def _sign_payload(payload):
    private_key, _ = _get_keys()
    signature = private_key.sign(
        _canonical(payload).encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def _verify_payload(payload, signature):
    if not signature:
        return False
    _, public_key = _get_keys()
    try:
        public_key.verify(
            base64.b64decode(signature),
            _canonical(payload).encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def _binding_hash(mandate_id, amount, payee, currency):
    payload = {
        "mandate_id": mandate_id,
        "amount": amount,
        "payee": payee,
        "currency": currency,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


CHAIN_FIELDS = (
    "jti", "mandate_id", "agent", "amount", "payee", "currency",
    "binding_hash", "issued_at", "expires_at", "signature",
)


def _auth_chain_hash(auth, prev_chain_hash):
    # Chain covers only the immutable authorization terms - settlement
    # fields (status/settlement_ref/settled_at) change later and must not
    # break verification of the chain itself.
    payload = {k: auth.get(k) for k in CHAIN_FIELDS}
    return hashlib.sha256(
        (_canonical(payload) + prev_chain_hash).encode("utf-8")
    ).hexdigest()


def _auth_sign_payload(auth):
    return {
        "jti": auth["jti"],
        "mandate_id": auth["mandate_id"],
        "binding_hash": auth["binding_hash"],
        "issued_at": auth["issued_at"],
        "expires_at": auth["expires_at"],
    }

# ---- 1. INTENT MANDATE ----

def create_intent_mandate(
    principal,
    agent,
    max_per_payment,
    max_total,
    currency="USDC",
    payees=None,
    scope=DEFAULT_SCOPE,
    ttl_seconds=86400,
):
    try:
        if not principal or not agent:
            return {"error": "INVALID_INPUT", "detail": "principal and agent required"}
        if not isinstance(max_per_payment, int) or max_per_payment <= 0:
            return {"error": "INVALID_INPUT", "detail": "max_per_payment must be positive int"}
        if not isinstance(max_total, int) or max_total <= 0:
            return {"error": "INVALID_INPUT", "detail": "max_total must be positive int"}
        if max_per_payment > max_total:
            return {"error": "INVALID_INPUT", "detail": "max_per_payment cannot exceed max_total"}

        now = _now()
        mandate = {
            "mandate_id": str(uuid.uuid4()),
            "principal": principal,
            "agent": agent,
            "scope": scope,
            "currency": currency,
            "max_per_payment": max_per_payment,
            "max_total": max_total,
            "payees": list(payees) if payees else [],
            "issued_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=ttl_seconds)),
            "spent": 0,
            "payments_count": 0,
            "revoked": False,
        }
        mandate["signature"] = _sign_payload({
            "mandate_id": mandate["mandate_id"],
            "principal": mandate["principal"],
            "agent": mandate["agent"],
            "currency": mandate["currency"],
            "max_per_payment": mandate["max_per_payment"],
            "max_total": mandate["max_total"],
            "payees": mandate["payees"],
            "issued_at": mandate["issued_at"],
            "expires_at": mandate["expires_at"],
        })

        save_mandate(mandate)
        log("MANDATE_ISSUE", {"mandate_id": mandate["mandate_id"], "agent": agent})
        record_receipt(
            scope=scope,
            decision="MANDATE_ISSUED",
            risk="high",
            reason=f"intent mandate for {agent} up to {max_total} {currency}",
            status="ACTIVE",
            agent=agent,
            metadata={
                "mandate_id": mandate["mandate_id"],
                "principal": principal,
                "max_total": max_total,
            },
            async_write=False,
        )
        logger.info(f"Intent mandate issued: {mandate['mandate_id']} agent: {agent}")
        return mandate
    except Exception as e:
        logger.error(f"Mandate issue failed: {str(e)}")
        return {"error": "MANDATE_ISSUE_FAILED", "detail": str(e)}


def revoke_mandate(mandate_id):
    mandate = get_mandate(mandate_id)
    if not mandate:
        return {"error": "MANDATE_NOT_FOUND"}
    set_mandate_revoked(mandate_id)
    log("MANDATE_REVOKE", {"mandate_id": mandate_id})
    record_receipt(
        scope=mandate["scope"],
        decision="MANDATE_REVOKED",
        risk="high",
        reason=f"mandate {mandate_id} revoked by principal",
        status="REVOKED",
        agent=mandate["agent"],
        metadata={"mandate_id": mandate_id},
        async_write=False,
    )
    return {"status": "MANDATE_REVOKED", "mandate_id": mandate_id}

# ---- 2. PAYMENT AUTHORIZATION (one-time, bound) ----

def authorize_payment(mandate_id, agent, amount, payee, currency=None, ttl_seconds=PAYMENT_AUTH_TTL_SECONDS):
    try:
        if not isinstance(amount, int) or amount <= 0:
            return {"error": "INVALID_AMOUNT", "detail": "amount must be positive int (smallest unit)"}
        if not payee:
            return {"error": "INVALID_INPUT", "detail": "payee required"}

        mandate = get_mandate(mandate_id)
        if not mandate:
            return {"error": "MANDATE_NOT_FOUND"}
        if mandate["revoked"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "MANDATE_REVOKED"})
            return {"error": "MANDATE_REVOKED"}
        if datetime.fromisoformat(mandate["expires_at"]) + timedelta(seconds=CLOCK_SKEW_SECONDS) < _now():
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "MANDATE_EXPIRED"})
            return {"error": "MANDATE_EXPIRED"}
        if agent != mandate["agent"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "AGENT_MISMATCH"})
            return {"error": "AGENT_MISMATCH"}

        currency = currency or mandate["currency"]
        if currency != mandate["currency"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "CURRENCY_MISMATCH"})
            return {"error": "CURRENCY_MISMATCH"}
        if mandate["payees"] and payee not in mandate["payees"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "PAYEE_NOT_ALLOWED"})
            return {"error": "PAYEE_NOT_ALLOWED", "detail": f"{payee} not in mandate allowlist"}
        if amount > mandate["max_per_payment"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "AMOUNT_LIMIT"})
            return {"error": "AMOUNT_LIMIT", "detail": f"amount {amount} exceeds max_per_payment {mandate['max_per_payment']}"}
        if mandate["spent"] + amount > mandate["max_total"]:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "BUDGET_EXHAUSTED"})
            return {"error": "BUDGET_EXHAUSTED", "detail": f"spent {mandate['spent']} + {amount} exceeds max_total {mandate['max_total']}"}

        now = _now()
        auth = {
            "jti": str(uuid.uuid4()),
            "mandate_id": mandate_id,
            "agent": agent,
            "amount": amount,
            "payee": payee,
            "currency": currency,
            "binding_hash": _binding_hash(mandate_id, amount, payee, currency),
            "issued_at": _iso(now),
            "expires_at": _iso(now + timedelta(seconds=ttl_seconds)),
            "status": "AUTHORIZED",
        }
        auth["signature"] = _sign_payload(_auth_sign_payload(auth))

        # Race-safe budget guard: atomic UPDATE re-checks max_total inside SQL.
        updated = increment_mandate_spend(mandate_id, amount)
        if not updated:
            log("PAYMENT_AUTH_FAIL", {"mandate_id": mandate_id, "reason": "BUDGET_EXHAUSTED"})
            return {"error": "BUDGET_EXHAUSTED", "detail": "budget guard rejected the spend"}

        prev_chain = "GENESIS"
        existing = list_payment_auths(mandate_id)
        if existing:
            prev_chain = existing[-1]["chain_hash"]
        auth["chain_hash"] = _auth_chain_hash(auth, prev_chain)

        save_payment_auth(auth)
        log("PAYMENT_AUTH", {"jti": auth["jti"], "mandate_id": mandate_id, "amount": amount, "payee": payee})
        record_receipt(
            scope=mandate["scope"],
            decision="PAYMENT_AUTHORIZED",
            risk="high",
            reason=f"{amount} {currency} to {payee} under mandate {mandate_id}",
            status="AUTHORIZED",
            agent=agent,
            metadata={"jti": auth["jti"], "mandate_id": mandate_id, "amount": amount, "payee": payee},
            async_write=False,
        )
        logger.info(f"Payment authorized: {auth['jti']} amount: {amount} payee: {payee}")
        return auth
    except Exception as e:
        logger.error(f"Payment authorize failed: {str(e)}")
        return {"error": "PAYMENT_AUTH_FAILED", "detail": str(e)}

# ---- 3. SETTLEMENT ----

def settle_payment(jti, settlement_ref):
    try:
        if not settlement_ref:
            return {"error": "SETTLEMENT_REF_REQUIRED", "detail": "settlement reference (e.g. x402 tx hash) required"}

        auth = get_payment_auth(jti)
        if not auth:
            return {"error": "AUTH_NOT_FOUND"}
        if auth["status"] == "SETTLED":
            log("PAYMENT_SETTLE_FAIL", {"jti": jti, "reason": "ALREADY_SETTLED"})
            return {"error": "ALREADY_SETTLED"}
        if auth["status"] == "CANCELLED":
            return {"error": "AUTH_CANCELLED"}
        if datetime.fromisoformat(auth["expires_at"]) + timedelta(seconds=CLOCK_SKEW_SECONDS) < _now():
            log("PAYMENT_SETTLE_FAIL", {"jti": jti, "reason": "AUTH_EXPIRED"})
            return {"error": "AUTH_EXPIRED"}
        if auth["binding_hash"] != _binding_hash(auth["mandate_id"], auth["amount"], auth["payee"], auth["currency"]):
            log("PAYMENT_SETTLE_FAIL", {"jti": jti, "reason": "BINDING_MISMATCH"})
            return {"error": "BINDING_MISMATCH", "detail": "payment terms do not match the authorized binding"}
        if not _verify_payload(_auth_sign_payload(auth), auth.get("signature")):
            log("PAYMENT_SETTLE_FAIL", {"jti": jti, "reason": "INVALID_SIGNATURE"})
            return {"error": "INVALID_SIGNATURE", "detail": "payment terms were tampered after authorization"}

        settled_at = _iso(_now())
        update_payment_auth(jti, {"status": "SETTLED", "settlement_ref": settlement_ref, "settled_at": settled_at})
        log("PAYMENT_SETTLE", {"jti": jti, "settlement_ref": settlement_ref})

        receipt = record_receipt(
            scope="payment.settle",
            decision="PAYMENT_SETTLED",
            risk="high",
            reason=f"{auth['amount']} {auth['currency']} to {auth['payee']} settled ({settlement_ref})",
            status="SETTLED",
            agent=auth["agent"],
            metadata={
                "jti": jti,
                "mandate_id": auth["mandate_id"],
                "amount": auth["amount"],
                "payee": auth["payee"],
                "settlement_ref": settlement_ref,
            },
            async_write=False,
        )
        logger.info(f"Payment settled: {jti} ref: {settlement_ref}")
        return {"status": "SETTLED", "jti": jti, "receipt_hash": receipt["receipt_hash"]}
    except Exception as e:
        logger.error(f"Settle failed: {str(e)}")
        return {"error": "SETTLE_FAILED", "detail": str(e)}

# ---- 4. VERIFICATION ----

def verify_payment_auth(jti):
    """Read-only third-party verification of a payment authorization."""
    auth = get_payment_auth(jti)
    if not auth:
        return {"error": "AUTH_NOT_FOUND"}
    sig_valid = _verify_payload(_auth_sign_payload(auth), auth.get("signature"))
    binding_valid = auth["binding_hash"] == _binding_hash(
        auth["mandate_id"], auth["amount"], auth["payee"], auth["currency"]
    )
    return {
        "status": "OK",
        "jti": jti,
        "mandate_id": auth["mandate_id"],
        "amount": auth["amount"],
        "payee": auth["payee"],
        "currency": auth["currency"],
        "payment_status": auth["status"],
        "signature_valid": sig_valid,
        "binding_valid": binding_valid,
    }


def verify_payment_chain(mandate_id):
    """Recompute the hash chain over a mandate's payment auths. Tamper detection."""
    auths = list_payment_auths(mandate_id)
    prev_hash = "GENESIS"
    for auth in auths:
        stored = auth.get("chain_hash")
        computed = _auth_chain_hash(auth, prev_hash)
        if computed != stored:
            return False
        prev_hash = stored
    return True


# ---- 5. DISPUTE BUNDLE ----

def export_dispute_bundle(mandate_id):
    """Verifiable evidence bundle: mandate + all payment auths + chain proof.

    This is what an insurer, platform, or court can independently verify
    without trusting the operator - signatures and chain hashes only.
    """
    mandate = get_mandate(mandate_id)
    if not mandate:
        return {"error": "MANDATE_NOT_FOUND"}
    auths = list_payment_auths(mandate_id)
    for auth in auths:
        auth["signature_valid"] = _verify_payload(_auth_sign_payload(auth), auth.get("signature"))
        auth["binding_valid"] = auth["binding_hash"] == _binding_hash(
            auth["mandate_id"], auth["amount"], auth["payee"], auth["currency"]
        )
    bundle = {
        "bundle_type": "AION_DISPUTE_BUNDLE",
        "mandate": mandate,
        "payments": auths,
        "chain_intact": verify_payment_chain(mandate_id),
        "total_settled": sum(a["amount"] for a in auths if a["status"] == "SETTLED"),
        "total_authorized": sum(a["amount"] for a in auths),
        "exported_at": _iso(_now()),
    }
    bundle["bundle_hash"] = hashlib.sha256(
        _canonical(bundle).encode("utf-8")
    ).hexdigest()
    return bundle



