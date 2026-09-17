"""AION x402 ADAPTER - Agent Payment Enforcement Demo

x402 (Linux Foundation) moves the money.
AION enforces what the human actually authorized.

Question: Can an x402 seller overcharge, swap the payee, or double-spend?
Answer:   Watch every attempt get blocked, cryptographically.

Run:  python x402_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "aion_pkg"))

from aion.payments import create_intent_mandate, export_dispute_bundle
from aion.x402 import authorize_x402, check_x402_against_mandate, settle_x402

ROOT = Path(__file__).parent

results = []


def log(test_name, expected, actual, passed):
    status = "PASS" if passed else "FAIL"
    results.append({"test": test_name, "expected": expected, "actual": actual, "status": status})
    marker = "+" if passed else "x"
    print(f"  [{status}] {marker} {test_name}")
    print(f"         Expected : {expected}")
    print(f"         Got      : {actual}")
    print()


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def banner():
    print("\n" + "=" * 68)
    print("  AION x402 ADAPTER - MANDATE ENFORCEMENT FOR AGENT PAYMENTS")
    print("  'x402 moves the money. AION enforces the intent.'")
    print("=" * 68 + "\n")
    print("  x402 principle (their own spec):")
    print('    "funds must only move in accordance with client intentions"')
    print("  ...but x402 has no way to sign, bind, or prove those intentions.")
    print("  AION adds that missing layer.\n")


def scene_1_mandate():
    print("-- SCENE 1: The principal signs the rules --------------------\n")
    print("  Alice -> her agent: $10.00 budget, $5.00 per payment,")
    print("  and ONLY api:weather may be paid. RSA-signed, not negotiable.\n")

    mandate = create_intent_mandate(
        principal="user:alice",
        agent="agent:shopbot",
        max_per_payment=5000,
        max_total=10000,
        payees=["api:weather"],
    )
    assert "error" not in mandate, mandate
    print(f"  mandate_id : {mandate['mandate_id']}")
    print(f"  signature  : {mandate['signature'][:32]}... (RSA-2048)\n")
    return mandate


def scene_2_preflight(mandate, requirements):
    print("-- SCENE 2: x402 PAYMENT-REQUIRED -> AION pre-flight ----------\n")
    print("  Seller asks : 3000 (0.003 USDC) on base-sepolia, payTo api:weather")
    print("  Agent asks AION: 'am I allowed to make this payment?'\n")

    auth = authorize_x402(mandate["mandate_id"], requirements)
    log(
        "Legit x402 payment is authorized (one-time, bound to exact terms)",
        "decision=allow",
        f"decision={auth.get('decision')} amount={auth.get('amount')} payee={auth.get('payee')}",
        auth.get("decision") == "allow",
    )
    return auth


def scene_3_seller_verify(mandate, requirements, auth):
    print("-- SCENE 3: Seller-side check (inside x402 /verify) -----------\n")
    print("  The seller does not trust the agent. It asks AION directly:\n")

    check = check_x402_against_mandate(mandate["mandate_id"], requirements, auth["aion_jti"])
    log(
        "Valid auth passes seller-side mandate verification",
        "decision=allow",
        f"decision={check.get('decision')} status={check.get('payment_status')}",
        check.get("decision") == "allow",
    )

def scene_4_settle(auth, payment_response):
    print("-- SCENE 4: x402 settlement -> bound into AION receipt chain --\n")
    print("  Facilitator settled on-chain. Its tx hash now becomes the")
    print("  AION settlement reference, so the receipt carries real proof.\n")

    result = settle_x402(auth["aion_jti"], payment_response)
    log(
        "Settlement is bound to the one-time auth with on-chain tx hash",
        "decision=settled + receipt_hash",
        f"decision={result.get('decision')} ref={result.get('settlement_ref')}",
        result.get("decision") == "settled" and bool(result.get("receipt_hash")),
    )
    return result


def scene_5_replay(mandate, requirements, auth):
    print("-- ATTACK 1: Seller replays the same auth (double-spend) ------\n")
    print("  The seller already settled. Can it settle the SAME auth twice?\n")

    check = check_x402_against_mandate(mandate["mandate_id"], requirements, auth["aion_jti"])
    log(
        "Replayed auth is rejected after settlement",
        "decision=block reason=AUTH_ALREADY_SETTLED",
        f"decision={check.get('decision')} reason={check.get('reason')}",
        check.get("decision") == "block" and check.get("reason") == "AUTH_ALREADY_SETTLED",
    )


def scene_6_overcharge(mandate, overlimit_requirements):
    print("-- ATTACK 2: Seller inflates the price ($0.003 -> $0.09) ------\n")
    print("  Description says 'Annual premium'. Prompt injection says pay it.")
    print("  The mandate says $5.00 max per payment. Who wins?\n")

    auth = authorize_x402(mandate["mandate_id"], overlimit_requirements)
    log(
        "Inflated x402 price is blocked by the per-payment limit",
        "decision=block reason=AMOUNT_LIMIT",
        f"decision={auth.get('decision')} reason={auth.get('reason')}",
        auth.get("decision") == "block" and auth.get("reason") == "AMOUNT_LIMIT",
    )
    print(f"  detail: {auth.get('detail')}\n")


def scene_7_rogue_payee(mandate, rogue_requirements):
    print("-- ATTACK 3: Rogue payee injected via prompt -------------------\n")
    print("  Amount is normal (3000), but payTo is 'api:attacker-wallet'")
    print("  and the resource points at evil.example. AION checks the\n"
          "  signed allowlist, not the description.\n")

    auth = authorize_x402(mandate["mandate_id"], rogue_requirements)
    log(
        "Payment to a non-allowlisted payee is blocked",
        "decision=block reason=PAYEE_NOT_ALLOWED",
        f"decision={auth.get('decision')} reason={auth.get('reason')}",
        auth.get("decision") == "block" and auth.get("reason") == "PAYEE_NOT_ALLOWED",
    )
    print(f"  detail: {auth.get('detail')}\n")

def scene_8_dispute(mandate):
    print("-- SCENE 5: Dispute bundle (third-party verifiable) ------------\n")
    print("  Seller now claims: 'your agent agreed to pay $0.09 twice'.")
    print("  Alice exports the evidence. No one has to trust AION -")
    print("  the bundle is verified from RSA signatures and hash chain alone.\n")

    bundle = export_dispute_bundle(mandate["mandate_id"])
    assert "error" not in bundle, bundle

    payments = bundle["payments"]
    print(f"  bundle_hash       : {bundle['bundle_hash'][:32]}...")
    print(f"  chain_intact      : {bundle['chain_intact']}")
    print(f"  total_authorized  : {bundle['total_authorized']} (smallest unit)")
    print(f"  total_settled     : {bundle['total_settled']} (smallest unit)")
    print(f"  payments recorded : {len(payments)}\n")

    all_valid = all(p["signature_valid"] and p["binding_valid"] for p in payments)
    log(
        "Dispute bundle verifies: signatures valid, bindings intact, chain unbroken",
        "chain_intact=True, all signatures valid",
        f"chain_intact={bundle['chain_intact']} all_signatures_valid={all_valid} payments={len(payments)}",
        bundle["chain_intact"] is True and all_valid,
    )

    log(
        "Only 1 payment was authorized - the claimed extra one never existed",
        "total_authorized=3000 (one payment)",
        f"total_authorized={bundle['total_authorized']}",
        bundle["total_authorized"] == 3000,
    )
    return bundle


def summary():
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print("=" * 68)
    print(f"  RESULT: {passed}/{total} checks passed")
    print("=" * 68)
    print()
    print("  x402 moves money. AION enforces that money moves ONLY where")
    print("  the human signed. Overcharge? Blocked. Rogue payee? Blocked.")
    print("  Double-spend? Blocked. Dispute? Provable by math alone.")
    print()
    if passed != total:
        for r in results:
            if r["status"] != "PASS":
                print(f"  FAILED: {r['test']} | expected {r['expected']} | got {r['actual']}")
        return 1
    return 0


def main():
    banner()

    requirements = load("x402-requirements.json")
    overlimit = load("x402-attack-overlimit.json")
    rogue = load("x402-attack-rogue-payee.json")
    payment_response = load("x402-response.json")

    mandate = scene_1_mandate()
    auth = scene_2_preflight(mandate, requirements)
    scene_3_seller_verify(mandate, requirements, auth)
    scene_4_settle(auth, payment_response)
    scene_5_replay(mandate, requirements, auth)
    scene_6_overcharge(mandate, overlimit)
    scene_7_rogue_payee(mandate, rogue)
    scene_8_dispute(mandate)

    return summary()


if __name__ == "__main__":
    raise SystemExit(main())
