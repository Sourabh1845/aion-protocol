"""AION PAYMENT RAILS — Rogue Agent Attack Demo

Question: Can an autonomous agent steal money?
Answer:   Watch it fail. Every attack blocked + every tamper detected.

Run:  python payments_demo.py
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "aion_pkg"))

from aion.payments import (
    authorize_payment,
    create_intent_mandate,
    export_dispute_bundle,
    settle_payment,
    verify_payment_auth,
    verify_payment_chain,
)

DB_FILE = Path(__file__).parent / "aion_pkg" / "storage" / "aion.db"

results = []


def log(test_name, expected, actual, passed):
    status = "PASS" if passed else "FAIL"
    results.append({"test": test_name, "expected": expected, "actual": actual, "status": status})
    marker = "✓" if passed else "✗"
    print(f"  [{status}] {marker} {test_name}")
    print(f"         Expected : {expected}")
    print(f"         Got      : {actual}")
    print()


def dollars(cents):
    return f"${cents / 100:.2f}"


def banner():
    print("\n" + "=" * 65)
    print("  AION PAYMENT RAILS — ROGUE AGENT ATTACK DEMO")
    print("  'Can an AI agent steal money? Watch it fail.'")
    print("=" * 65 + "\n")


def scene_0_setup():
    print("── SCENE 0: The Principal sets the rules ────────────────────\n")
    print("  Alice gives her shopping agent a signed Intent Mandate:")
    print("    • Budget cap      : $10.00 total (max_total=1000 cents)")
    print("    • Per-payment cap : $5.00  (max_per_payment=500 cents)")
    print("    • Payee allowlist : ['api:bookstore'] ONLY")
    print("    • Every rule RSA-signed. Every payment hash-chained.\n")

    mandate = create_intent_mandate(
        principal="user:alice",
        agent="agent:shopbot",
        max_per_payment=500,
        max_total=1000,
        currency="USDC",
        payees=["api:bookstore"],
    )
    ok = "error" not in mandate and mandate["signature"]
    log("0.1  Intent Mandate issued + RSA-signed",
        "signed mandate with budget + payee allowlist",
        f"mandate_id={mandate.get('mandate_id', '?')[:8]}... signature={bool(mandate.get('signature'))}",
        ok)
    return mandate


def scene_1_honest_payment(mandate):
    print("── SCENE 1: The Honest Agent pays ───────────────────────────\n")

    auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 300, "api:bookstore")
    ok = "error" not in auth and auth.get("binding_hash")
    log("1.1  Agent pays $3.00 to allowed bookstore",
        "AUTHORIZED, bound to exact amount + payee",
        f"jti={auth.get('jti', '?')[:8]}... status={auth.get('status', auth.get('error'))}", ok)
    if not ok:
        return None

    result = settle_payment(auth["jti"], "x402:tx_book_0xabc")
    ok2 = result.get("status") == "SETTLED" and result.get("receipt_hash")
    log("1.2  Settlement proof attached (x402 tx)",
        "SETTLED + receipt hash",
        f"status={result.get('status')} receipt={str(result.get('receipt_hash'))[:16]}...", ok2)

    check = verify_payment_auth(auth["jti"])
    ok3 = check.get("signature_valid") and check.get("binding_valid")
    log("1.3  Independent third-party verification",
        "signature_valid=True binding_valid=True",
        f"signature_valid={check.get('signature_valid')} binding_valid={check.get('binding_valid')}", ok3)
    return auth


# ==== SCENES 2-4 APPENDED BELOW ====


def scene_2_rogue_attacks(mandate):
    print("── SCENE 2: The Rogue Agent attacks ─────────────────────────\n")
    print("  A compromised agent tries to move money out. Watch:\n")

    mid = mandate["mandate_id"]

    # Attack 2.1 — payee swap: money to attacker wallet
    r = authorize_payment(mid, "agent:shopbot", 400, "attacker:0xdead")
    log("2.1  Redirect payment to attacker wallet",
        "PAYEE_NOT_ALLOWED (allowlist violation)",
        str(r.get("error", r)), r.get("error") == "PAYEE_NOT_ALLOWED")

    # Attack 2.2 — inflate amount beyond per-payment cap
    r = authorize_payment(mid, "agent:shopbot", 10000, "api:bookstore")
    log("2.2  Inflate single payment to $100.00",
        "AMOUNT_LIMIT (per-payment cap $5.00)",
        str(r.get("error", r)), r.get("error") == "AMOUNT_LIMIT")

    # Attack 2.3 — budget drain (two-step: burn budget on a legit-looking
    # purchase, then try to overspend what's left)
    r = authorize_payment(mid, "agent:shopbot", 500, "api:bookstore")
    step_a = r.get("status") == "AUTHORIZED"
    r = authorize_payment(mid, "agent:shopbot", 400, "api:bookstore")
    log("2.3  Burn budget on legit buy, then overspend ($4 of $2 left)",
        "step1 AUTHORIZED -> step2 BUDGET_EXHAUSTED",
        f"step1={'AUTHORIZED' if step_a else r.get('error')} -> step2={r.get('error', r)}",
        step_a and r.get("error") == "BUDGET_EXHAUSTED")

    # Attack 2.4 — impersonate another agent on the same mandate
    r = authorize_payment(mid, "agent:rogue", 100, "api:bookstore")
    log("2.4  Rogue process impersonates the mandate's agent",
        "AGENT_MISMATCH",
        str(r.get("error", r)), r.get("error") == "AGENT_MISMATCH")

    # Attack 2.5 — fake/unknown mandate id
    r = authorize_payment("00000000-0000-0000-0000-000000000000", "agent:shopbot", 100, "api:bookstore")
    log("2.5  Forge a mandate_id out of thin air",
        "MANDATE_NOT_FOUND",
        str(r.get("error", r)), r.get("error") == "MANDATE_NOT_FOUND")


def scene_3_tamper_detection(mandate):
    print("── SCENE 3: The Insider — direct database tamper ────────────\n")
    print("  Rogue process authorizes a $1.00 payment, then edits the")
    print("  ledger directly: $1.00 -> $99.99. Can it settle?\n")

    mid = mandate["mandate_id"]

    # Fresh UNSETTLED payment — budget: $8 spent, $2 left, asks $1 (legal)
    fresh = authorize_payment(mid, "agent:shopbot", 100, "api:bookstore")
    if "error" in fresh:
        log("3.0  Fresh payment for tamper scenario", "AUTHORIZED", str(fresh), False)
        return
    target = fresh["jti"]

    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("UPDATE payment_auths SET amount=9999 WHERE jti=?", (target,))
    conn.commit()
    conn.close()

    r = settle_payment(target, "x402:tx_attacker_0xdead")
    log("3.1  Try to SETTLE the inflated payment",
        "BINDING_MISMATCH (terms no longer match signature)",
        str(r.get("error", r)), r.get("error") == "BINDING_MISMATCH")

    chain_ok = verify_payment_chain(mandate["mandate_id"])
    log("3.2  Hash-chain verification over all payments",
        "chain broken = False (tamper detected)",
        f"chain_intact={chain_ok}", chain_ok is False)

    check = verify_payment_auth(target)
    log("3.3  Pinpoint WHERE tampering happened",
        "signature_valid=True but binding_valid=False",
        f"signature_valid={check.get('signature_valid')} binding_valid={check.get('binding_valid')}",
        check.get("signature_valid") is True and check.get("binding_valid") is False)


def scene_4_dispute_bundle(mandate):
    print("── SCENE 4: The Evidence — dispute bundle for the court ─────\n")

    bundle = export_dispute_bundle(mandate["mandate_id"])
    if "error" in bundle:
        log("4.1  Export dispute bundle", "verifiable bundle", str(bundle), False)
        return

    log("4.1  Export dispute bundle",
        "bundle_type + bundle_hash exported",
        f"hash={bundle['bundle_hash'][:16]}... chain_intact={bundle['chain_intact']}",
        bundle["bundle_type"] == "AION_DISPUTE_BUNDLE")

    tampered = [p for p in bundle["payments"] if not p["binding_valid"]]
    log("4.2  Bundle pinpoints the tampered payment",
        "exactly 1 payment flagged (binding_valid=False)",
        f"flagged={len(tampered)}",
        len(tampered) == 1)

    print("  ┌─ DISPUTE BUNDLE (what a judge/insurer sees) ────────────")
    print(f"  │ Mandate   : {bundle['mandate']['mandate_id'][:8]}... principal={bundle['mandate']['principal']}")
    print(f"  │ Budget    : {dollars(bundle['mandate']['max_total'])} | Spent: {dollars(bundle['mandate']['spent'])}")
    for p in bundle["payments"]:
        amt = dollars(p["amount"])
        verdict = "TAMPERED" if not p["binding_valid"] else p["status"]
        print(f"  │ Payment   : {p['jti'][:8]}... {amt:>7} -> {p['payee']}  [{verdict}]")
    print(f"  │ Chain     : {'INTACT' if bundle['chain_intact'] else 'BROKEN — tampering detected'}")
    print(f"  │ Evidence  : bundle_hash={bundle['bundle_hash'][:24]}...")
    print("  └──────────────────────────────────────────────────────────\n")


def final_report():
    print("=" * 65)
    print("  FINAL REPORT")
    print("=" * 65)
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n  Total Checks : {total}")
    print(f"  Passed       : {passed}")
    print(f"  Failed       : {total - passed}")
    print(f"  Score        : {passed}/{total}")

    if passed == total:
        print("\n  ✓ Every attack blocked. Every tamper detected. Money stayed safe.")
        print("  ✓ No prompt could do this — this is cryptography, not policy.")
    else:
        print("\n  ✗ Some checks failed:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    ✗ {r['test']} — got {r['actual']}")
    print("\n" + "=" * 65 + "\n")


def main():
    banner()
    mandate = scene_0_setup()
    if "error" in mandate:
        print(f"FATAL: mandate setup failed: {mandate}")
        sys.exit(1)
    scene_1_honest_payment(mandate)
    scene_2_rogue_attacks(mandate)
    scene_3_tamper_detection(mandate)
    scene_4_dispute_bundle(mandate)
    final_report()
    sys.exit(0 if all(r["status"] == "PASS" for r in results) else 1)


if __name__ == "__main__":
    main()
