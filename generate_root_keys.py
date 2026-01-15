from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Generate root keypair
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Save private key (KEEP SAFE)
with open("root_private.key", "wb") as f:
    f.write(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    )

# Save public key (USED FOR VERIFY / ENFORCE)
with open("root_public.key", "wb") as f:
    f.write(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )

print("ROOT KEYS GENERATED SUCCESSFULLY")
