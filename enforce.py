import json
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

LEDGER_FILE = "authority_ledger.json"
PUBLIC_KEY_FILE = "root_public_key.pem"


def load_ledger():
    with open(LEDGER_FILE, "r") as f:
        return json.load(f)


def load_public_key():
    with open(PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def find_authority(jti, ledger):
    return next((a for a in ledger if a["jti"] == jti), None)


def verify_signature(authority, public_key):
    payload = authority.copy()
    signature = bytes.fromhex(payload.pop("signature"))

    data = json.dumps(payload, sort_keys=True).encode()

    public_key.verify(
        signature,
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )


def validate_chain(authority, ledger):
    current = authority

    while True:
        if current.get("revoked"):
            raise Exception("Authority revoked")

        if current["expiry"] < int(time.time()):
            raise Exception("Authority expired")

        parent_jti = current.get("parent")
        if parent_jti is None:
            # ROOT reached
            return

        parent = find_authority(parent_jti, ledger)
        if not parent:
            raise Exception("Broken trust chain (parent missing)")

        if parent["level"] != current["level"] - 1:
            raise Exception("Invalid trust level chain")

        current = parent


def main():
    ledger = load_ledger()
    public_key = load_public_key()

    jti = input("Enter authority JTI to enforce: ").strip()

    authority = find_authority(jti, ledger)
    if not authority:
        print("ENFORCE FAIL: Authority not found")
        return

    try:
        verify_signature(authority, public_key)
        validate_chain(authority, ledger)

        # Domain enforcement for non-root
        if authority["level"] > 0:
            if authority["domain"] != "ops":
                raise Exception("Domain violation")

        # Replay protection
        if authority.get("consumed"):
            raise Exception("Authority already consumed (replay?)")

        authority["consumed"] = True

        with open(LEDGER_FILE, "w") as f:
            json.dump(ledger, f, indent=2)

        print(f"ENFORCE PASS: Authority valid, JTI={jti}, chain verified")

    except Exception as e:
        print(f"ENFORCE FAIL: {e}")


if __name__ == "__main__":
    main()
