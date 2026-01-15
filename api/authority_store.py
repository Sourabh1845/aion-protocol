import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ROOT_FILE = DATA_DIR / "root.json"


def load_root():
    if not ROOT_FILE.exists():
        return None
    with open(ROOT_FILE, "r") as f:
        return json.load(f)


def load_authority(jti: str):
    if jti == "ROOT":
        return load_root()

    auth_file = DATA_DIR / f"{jti}.json"
    if not auth_file.exists():
        return None

    with open(auth_file, "r") as f:
        return json.load(f)
