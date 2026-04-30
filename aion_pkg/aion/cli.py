import glob
import json
import sys
from pathlib import Path

from aion.authority import issue, revoke, verify
from aion.enforce import enforce
from aion.policy import DEFAULT_POLICY
from aion.receipts import RECEIPT_DIR


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


def main():
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

    else:
        print(f"Unknown command: {cmd}")
        _print_usage()


if __name__ == "__main__":
    main()
