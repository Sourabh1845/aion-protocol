import glob
import json
import sys
from pathlib import Path

from aion.authority import issue, revoke, verify
from aion.cloud import upload_latest_receipt
from aion.enforce import enforce
from aion.policy import DEFAULT_POLICY
from aion.receipts import RECEIPT_DIR
from aion.scan import print_report, report_to_json, scan_path


def _print_usage():
    print("Usage: aion <command> [args]")
    print("")
    print("Commands:")
    print("  issue <scope>")
    print("  verify <jti> <scope>")
    print("  enforce <jti> <scope>")
    print("  revoke <jti>")
    print("  policy-init")
    print("  receipts [limit]")
    print("  guard-demo")
    print("  scan [path] [--json]")
    print("  cloud-sync")
    print("  mandate-create <agent> <max_per_payment> <max_total> [payees comma-sep]")
    print("  mandate-revoke <mandate_id>")
    print("  pay <mandate_id> <amount> <payee>")
    print("  settle <jti> <settlement_ref>")
    print("  pay-verify <jti>")
    print("  pay-chain <mandate_id>")
    print("  dispute <mandate_id> [--save]")
    print("  x402-pay <mandate_id> <requirements_json|@file> [--agent X] [--amount N]")
    print("  x402-check <mandate_id> <requirements_json|@file> <jti>")
    print("  x402-settle <jti> <payment_response_json|@file>")
    print("  anchor <mandate_id>")
    print("  anchor-verify <mandate_id>")
    print("  anchors")
    print("  demo                    # 60-second end-to-end story")
    print("  doctor                  # verify your install")
    print("  example <name>          # quickstart | langchain_agent | crewai_agent")


def _policy_init():
    path = Path("aion-policy.json")
    if path.exists():
        print("aion-policy.json already exists")
        return

    with path.open("w", encoding="utf-8") as f:
        json.dump(DEFAULT_POLICY, f, indent=2, sort_keys=True)

    print("Created aion-policy.json")


def _receipts(limit=10):
    pattern = str(RECEIPT_DIR / "*.json")
    files = glob.glob(pattern)

    if not files:
        print("No AION receipts found")
        return

    receipts = []
    skipped = 0

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                receipts.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            skipped += 1

    if skipped:
        print(f"Skipped {skipped} unreadable receipt file(s)")

    if not receipts:
        print("No readable AION receipts found")
        return

    receipts.sort(key=lambda item: item.get("timestamp", ""), reverse=True)

    for receipt in receipts[:limit]:
        print(
            f"{receipt.get('timestamp')} | "
            f"{receipt.get('status')} | "
            f"{receipt.get('decision')} | "
            f"{receipt.get('risk')} | "
            f"{receipt.get('scope')} | "
            f"{receipt.get('receipt_id')}"
        )


def _guard_demo():
    from aion.guard import AIONApprovalRequired, AIONBlockedError, guard

    @guard(
        scope="file.read",
        agent="cli-demo-agent",
        metadata_factory=lambda path: {"path": path},
    )
    def read_file(path):
        return f"read {path}"

    @guard(
        scope="shell.run",
        agent="cli-demo-agent",
        metadata_factory=lambda command: {"command": command},
    )
    def run_shell(command):
        return f"executed {command}"

    print("\n--- Low-risk action: file.read ---")
    print(json.dumps(read_file("README.md"), indent=2))

    print("\n--- Forbidden action: shell.run rm -rf ---")
    try:
        print(json.dumps(run_shell("rm -rf important"), indent=2))
    except AIONBlockedError as exc:
        print(f"Blocked correctly: {exc}")

    print("\n--- High-risk action: shell.run normal command ---")
    try:
        print(json.dumps(run_shell("echo hello"), indent=2))
    except AIONApprovalRequired as exc:
        print(f"Approval required correctly: {exc}")


def _mandate_create(agent, max_per_payment, max_total, payees_arg=None):
    from aion.payments import create_intent_mandate

    payees = [p for p in (payees_arg or "").split(",") if p]
    mandate = create_intent_mandate(
        principal="cli-user",
        agent=agent,
        max_per_payment=max_per_payment,
        max_total=max_total,
        payees=payees,
    )
    if "error" in mandate:
        print(json.dumps(mandate, indent=2))
        return
    print(f"Intent mandate issued for {agent}")
    print(f"mandate_id: {mandate['mandate_id']}")
    print(
        f"budget: {mandate['max_per_payment']}/payment, "
        f"{mandate['max_total']} total {mandate['currency']}"
    )
    if mandate["payees"]:
        print(f"payee allowlist: {', '.join(mandate['payees'])}")
    print("Rules are RSA-signed. Share mandate_id with the agent only.")


def _pay(mandate_id, amount, payee):
    from aion.payment_storage import get_mandate
    from aion.payments import authorize_payment

    mandate = get_mandate(mandate_id)
    if not mandate:
        print(json.dumps({"error": "MANDATE_NOT_FOUND"}, indent=2))
        return
    result = authorize_payment(mandate_id, mandate["agent"], amount, payee)
    if "error" in result:
        print(json.dumps(result, indent=2))
        return
    print(f"Payment authorized (one-time, bound to {amount} -> {payee})")
    print(f"jti: {result['jti']}")
    print(f"expires_at: {result['expires_at']}")
    print("Settle with: aion settle <jti> <settlement_ref>")


def _settle(jti, settlement_ref):
    from aion.payments import settle_payment

    print(json.dumps(settle_payment(jti, settlement_ref), indent=2))


def _pay_verify(jti):
    from aion.payments import verify_payment_auth

    print(json.dumps(verify_payment_auth(jti), indent=2))


def _pay_chain(mandate_id):
    from aion.payments import verify_payment_chain

    ok = verify_payment_chain(mandate_id)
    print(json.dumps({"mandate_id": mandate_id, "chain_intact": ok}, indent=2))


def _dispute(mandate_id, save=False):
    from aion.payments import export_dispute_bundle

    bundle = export_dispute_bundle(mandate_id)
    if "error" in bundle:
        print(json.dumps(bundle, indent=2))
        return
    if save:
        path = Path(f"dispute-bundle-{mandate_id}.json")
        path.write_text(
            json.dumps(bundle, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        print(f"Dispute bundle saved: {path}")
        print(f"bundle_hash: {bundle['bundle_hash']}")
        print(f"chain_intact: {bundle['chain_intact']}")
        print(
            f"total_settled: {bundle['total_settled']} / "
            f"total_authorized: {bundle['total_authorized']}"
        )
        return
    print(json.dumps(bundle, indent=2, default=str))


def _load_json_arg(value):
    """Accepts inline JSON or @path/to/file.json."""
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def _x402_pay(mandate_id, requirements_arg, agent=None, amount=None):
    from aion.x402 import authorize_x402

    requirements = _load_json_arg(requirements_arg)
    result = authorize_x402(
        mandate_id,
        requirements,
        agent=agent,
        amount=amount,
    )
    if result.get("decision") != "allow":
        print(f"BLOCKED: {result.get('reason')}")
        print(json.dumps(result, indent=2, default=str))
        return
    print(f"x402 payment authorized (one-time, bound to mandate {mandate_id})")
    print(f"aion_jti: {result['aion_jti']}")
    print(f"amount: {result['amount']} {result['currency']} -> {result['payee']}")
    print(f"scheme: {result['x402']['scheme']}  network: {result['x402']['network']}")
    print("Attach aion_jti to the x402 PAYMENT-SIGNATURE payload envelope.")
    print(json.dumps(result, indent=2, default=str))


def _x402_check(mandate_id, requirements_arg, jti):
    from aion.x402 import check_x402_against_mandate

    requirements = _load_json_arg(requirements_arg)
    result = check_x402_against_mandate(mandate_id, requirements, jti)
    if result.get("decision") == "allow":
        print(f"ALLOW: {result['amount']} {result['currency']} -> {result['payee']}")
        print(f"payment_status: {result['payment_status']}")
    else:
        print(f"BLOCKED: {result.get('reason')}")
    print(json.dumps(result, indent=2, default=str))


def _x402_settle(jti, payment_response_arg):
    from aion.x402 import settle_x402

    payment_response = _load_json_arg(payment_response_arg)
    result = settle_x402(jti, payment_response)
    if result.get("decision") == "settled":
        print(f"x402 settlement bound to receipt chain: {result['settlement_ref']}")
        print(f"receipt_hash: {result.get('receipt_hash')}")
    else:
        print(f"BLOCKED: {result.get('reason')}")
    print(json.dumps(result, indent=2, default=str))


def _force_utf8_stdio():
    """Windows consoles default to a legacy codepage (cp1252).

    Force UTF-8 on the CLI's own streams so proof output never prints as
    mojibake on a first run. Silently no-op on streams that cannot be
    reconfigured (e.g. a captured/redirected buffer).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    _force_utf8_stdio()
    if len(sys.argv) < 2:
        _print_usage()
        return

    cmd = sys.argv[1]

    if cmd == "issue":
        scope = sys.argv[2] if len(sys.argv) > 2 else "default"
        result = issue(scope)
        print(json.dumps(result, indent=2))

    elif cmd == "verify":
        jti = sys.argv[2]
        scope = sys.argv[3]
        print(json.dumps(verify(jti, scope), indent=2))

    elif cmd == "enforce":
        jti = sys.argv[2]
        scope = sys.argv[3]
        print(json.dumps(enforce(jti, scope), indent=2))

    elif cmd == "revoke":
        jti = sys.argv[2]
        print(json.dumps(revoke(jti), indent=2))

    elif cmd == "policy-init":
        _policy_init()

    elif cmd == "receipts":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        _receipts(limit)

    elif cmd == "guard-demo":
        _guard_demo()

    elif cmd == "scan":
        target = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--json" else "."
        json_output = "--json" in sys.argv
        report = scan_path(target)

        if json_output:
            print(report_to_json(report))
        else:
            print_report(report, limit=10)

    elif cmd == "cloud-sync":
        result = upload_latest_receipt()
        print(json.dumps(result, indent=2))

    elif cmd == "mandate-create":
        if len(sys.argv) < 5:
            print("Usage: aion mandate-create <agent> <max_per_payment> <max_total> [payees comma-sep]")
            return
        _mandate_create(
            sys.argv[2],
            int(sys.argv[3]),
            int(sys.argv[4]),
            sys.argv[5] if len(sys.argv) > 5 else None,
        )

    elif cmd == "mandate-revoke":
        from aion.payments import revoke_mandate
        print(json.dumps(revoke_mandate(sys.argv[2]), indent=2))

    elif cmd == "pay":
        if len(sys.argv) < 5:
            print("Usage: aion pay <mandate_id> <amount> <payee>")
            return
        _pay(sys.argv[2], int(sys.argv[3]), sys.argv[4])

    elif cmd == "settle":
        if len(sys.argv) < 4:
            print("Usage: aion settle <jti> <settlement_ref>")
            return
        _settle(sys.argv[2], sys.argv[3])

    elif cmd == "pay-verify":
        _pay_verify(sys.argv[2])

    elif cmd == "pay-chain":
        _pay_chain(sys.argv[2])

    elif cmd == "dispute":
        _dispute(sys.argv[2], save="--save" in sys.argv)

    elif cmd == "x402-pay":
        if len(sys.argv) < 4:
            print("Usage: aion x402-pay <mandate_id> <requirements_json|@file> [--agent X] [--amount N]")
            return
        agent = None
        amount = None
        if "--agent" in sys.argv:
            agent = sys.argv[sys.argv.index("--agent") + 1]
        if "--amount" in sys.argv:
            amount = int(sys.argv[sys.argv.index("--amount") + 1])
        _x402_pay(sys.argv[2], sys.argv[3], agent=agent, amount=amount)

    elif cmd == "x402-check":
        if len(sys.argv) < 5:
            print("Usage: aion x402-check <mandate_id> <requirements_json|@file> <jti>")
            return
        _x402_check(sys.argv[2], sys.argv[3], sys.argv[4])

    elif cmd == "x402-settle":
        if len(sys.argv) < 4:
            print("Usage: aion x402-settle <jti> <payment_response_json|@file>")
            return
        _x402_settle(sys.argv[2], sys.argv[3])

    elif cmd == "anchor":
        if len(sys.argv) < 3:
            print("Usage: aion anchor <mandate_id>")
            return
        from aion.anchoring import publish_root
        print(json.dumps(publish_root(sys.argv[2]), indent=2))

    elif cmd == "anchor-verify":
        if len(sys.argv) < 3:
            print("Usage: aion anchor-verify <mandate_id>")
            return
        from aion.anchoring import verify_against_published_root
        print(json.dumps(verify_against_published_root(sys.argv[2]), indent=2))

    elif cmd == "anchors":
        from aion.anchoring import list_anchors
        anchors = list_anchors()
        if not anchors:
            print("No anchors published yet")
            return
        for record in anchors:
            print(
                f"{record.get('anchored_at')} | "
                f"{record.get('mandate_id')[:13]} | "
                f"len={record.get('length')} | "
                f"root={str(record.get('root'))[:16]}..."
            )

    elif cmd == "demo":
        from aion.demo import run_demo
        run_demo()

    elif cmd == "doctor":
        from aion.doctor import run_doctor
        run_doctor()

    elif cmd == "example":
        if len(sys.argv) < 3:
            print("Usage: aion example <name>   (quickstart | langchain_agent | crewai_agent)")
            return
        from aion.examples import run_example
        run_example(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        _print_usage()


if __name__ == "__main__":
    main()
