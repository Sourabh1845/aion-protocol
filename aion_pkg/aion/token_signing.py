import json
import hashlib
import hmac
import base64
import os
from datetime import datetime, timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from pathlib import Path

KEYS_DIR = Path(__file__).parent.parent / "storage"
PRIVATE_KEY_FILE = KEYS_DIR / "aion_private_key.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "aion_public_key.pem"

def generate_keys():
    KEYS_DIR.mkdir(exist_ok=True)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    PRIVATE_KEY_FILE.write_bytes(private_pem)
    PUBLIC_KEY_FILE.write_bytes(public_pem)
    print("RSA keys generated successfully")
    return private_key, private_key.public_key()

def load_keys():
    if not PRIVATE_KEY_FILE.exists():
        return generate_keys()
    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_FILE.read_bytes(),
        password=None,
        backend=default_backend()
    )
    public_key = serialization.load_pem_public_key(
        PUBLIC_KEY_FILE.read_bytes(),
        backend=default_backend()
    )
    return private_key, public_key

def sign_token(auth: dict) -> str:
    private_key, _ = load_keys()
    payload = json.dumps({
        "jti": auth["jti"],
        "scope": auth["scope"],
        "issuer": auth["issuer"],
        "issued_at": auth["issued_at"],
        "expires_at": auth["expires_at"]
    }, sort_keys=True).encode()

    signature = private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()

def verify_token_signature(auth: dict, signature: str) -> bool:
    try:
        _, public_key = load_keys()
        payload = json.dumps({
            "jti": auth["jti"],
            "scope": auth["scope"],
            "issuer": auth["issuer"],
            "issued_at": auth["issued_at"],
            "expires_at": auth["expires_at"]
        }, sort_keys=True).encode()

        sig_bytes = base64.b64decode(signature)
        public_key.verify(
            sig_bytes,
            payload,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False