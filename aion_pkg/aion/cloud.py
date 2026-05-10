import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from aion.receipts import RECEIPT_DIR

DEFAULT_CLOUD_URL = "https://aion-cloud.onrender.com"


def _cloud_url():
    return os.getenv("AION_CLOUD_URL", DEFAULT_CLOUD_URL).rstrip("/")


def _api_key():
    return os.getenv("AION_CLOUD_API_KEY")


def upload_receipt(receipt, api_key=None, cloud_url=None):
    key = api_key or _api_key()
    if not key:
        return {"error": "AION_CLOUD_API_KEY is required"}

    url = (cloud_url or _cloud_url()).rstrip("/") + "/receipts"
    payload = json.dumps(receipt, default=str).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-AION-API-Key": key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        return {
            "error": "HTTP_ERROR",
            "status_code": exc.code,
            "detail": exc.read().decode("utf-8"),
        }
    except Exception as exc:
        return {"error": "UPLOAD_FAILED", "detail": str(exc)}


def load_receipt_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def latest_receipt_file():
    files = sorted(Path(RECEIPT_DIR).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return str(files[0]) if files else None


def upload_latest_receipt(api_key=None, cloud_url=None):
    path = latest_receipt_file()
    if not path:
        return {"error": "NO_RECEIPTS_FOUND"}

    receipt = load_receipt_file(path)
    return upload_receipt(receipt, api_key=api_key, cloud_url=cloud_url)
