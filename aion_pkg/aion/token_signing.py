import json
import base64
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from pathlib import Path

from aion.paths import key_file

# Hosted deployments keep the key in /etc/secrets (Render secret files, a
# read-only mount). Everywhere else it resolves through aion.paths, which
# defaults to ~/.aion/keys and migrates keys written by <= 2.3.2.
SECRETS_DIR = Path("/etc/secrets")


def _key_path(name):
    mounted = SECRETS_DIR / name
    if mounted.exists():
        return mounted
    return key_file(name)


def generate_keys():
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
    private_path = _key_path("aion_private_key.pem")
    public_path = _key_path("aion_public_key.pem")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return private_key, private_key.public_key()


def load_keys():
    private_path = _key_path("aion_private_key.pem")
    public_path = _key_path("aion_public_key.pem")
    if not private_path.exists():
        return generate_keys()
    private_key = serialization.load_pem_private_key(
        private_path.read_bytes(),
        password=None,
        backend=default_backend()
    )
    public_key = serialization.load_pem_public_key(
        public_path.read_bytes(),
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