"""`aion doctor` — install health check.

Verifies in ~5 seconds that a fresh install is actually usable:
Python version, cryptography backend, key material (with a backup
warning), policy file, storage/receipts writability, and CLI wiring.
"""

import sys

CHECKS = []


def _check(name, passed, detail=""):
    CHECKS.append((name, bool(passed), detail))
    mark = "PASS" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{mark}] {name}{suffix}")
    return bool(passed)


def run_doctor():
    print("\nAION DOCTOR — checking your install\n")

    _check("Python >= 3.10", sys.version_info >= (3, 10), sys.version.split()[0])

    try:
        import cryptography

        _check("cryptography backend", True, cryptography.__version__)
    except Exception as exc:  # pragma: no cover
        _check("cryptography backend", False, str(exc))
        _summary()
        return {"ok": False, "checks": CHECKS}

    from aion import __version__
    print(f"\n  aion-core version: {__version__}")

    print("\n-- signing keys --")
    try:
        from aion.token_signing import load_keys

        private_key, _ = load_keys()
        key_size = getattr(private_key, "key_size", "?")
        _check("RSA keypair loaded", True, f"{key_size}-bit")
        import aion.token_signing as ts

        from pathlib import Path

        key_file = Path(ts.PRIVATE_KEY_FILE)
        if key_file.exists():
            print(
                "  [WARN] private key is NOT backed up — copy it somewhere safe."
            )
            print(f"         ({key_file})")
            CHECKS.append(("key backup warning", True, "advisory"))
    except Exception as exc:
        _check("RSA keypair", False, str(exc))

    print("\n-- policy --")
    try:
        from aion.policy import load_policy

        policy = load_policy()
        rules = len(policy.get("tools", {}))
        err = policy.get("_load_error")
        _check("policy loaded", True, f"{rules} rules" + (f" | {err}" if err else ""))
    except Exception as exc:
        _check("policy loaded", False, str(exc))

    print("\n-- storage --")
    try:
        from aion.payment_storage import get_conn
        from aion.receipts import RECEIPT_DIR

        conn = get_conn()
        conn.execute("SELECT 1")
        conn.close()
        _check("payments DB writable", True)
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        probe = RECEIPT_DIR / ".doctor-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        _check("receipts dir writable", True, str(RECEIPT_DIR))
    except Exception as exc:
        _check("storage writable", False, str(exc))

    print("\n-- trust engine --")
    try:
        from aion.demo import run_demo

        _check("demo flow available", True, "run: aion demo")
    except Exception as exc:
        _check("demo flow available", False, str(exc))

    print("\n-- optional integrations (fine if missing) --")
    for module, label in (("langchain_core", "LangChain"), ("crewai", "CrewAI")):
        try:
            __import__(module)
            _check(f"{label} integration", True, "installed")
        except ImportError:
            CHECKS.append((f"{label} integration (optional)", True, "not installed - pip install to enable"))
            print(f"  [OPTIONAL] {label} not installed - enable with: pip install {module}")

    _summary()
    return {"ok": all(p for _, p, _ in CHECKS), "checks": CHECKS}


def _summary():
    failed = [name for name, passed, _ in CHECKS if not passed]
    print(f"\n{'=' * 62}")
    if not failed:
        print("HEALTHY - AION is ready. Start with:  aion demo")
        print("(garbled symbols? run:  set PYTHONIOENCODING=utf-8)")
    else:
        print(f"PROBLEMS FOUND ({len(failed)}):")
        for name in failed:
            print(f"  - {name}")
        print("Docs: https://github.com/Sourabh1845/aion-protocol#readme")
    print(f"{'=' * 62}\n")


if __name__ == "__main__":
    run_doctor()
