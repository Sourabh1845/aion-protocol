"""External anchoring: publish chain roots, verify against them later."""
import sqlite3
from pathlib import Path

from aion.anchoring import (
    compute_mandate_root,
    list_anchors,
    publish_root,
    verify_against_published_root,
)
from aion.payments import authorize_payment, create_intent_mandate

DB_FILE = Path(__file__).parent.parent / "storage" / "aion.db"


def _db():
    return sqlite3.connect(str(DB_FILE))


def _mandate_with_payment(amount=300, payee="api:weather"):
    mandate = create_intent_mandate(
        principal="user:anchor-test",
        agent="agent:anchor-test",
        max_per_payment=500,
        max_total=1000,
        payees=["api:weather", "api:news"],
    )
    assert "error" not in mandate, mandate
    auth = authorize_payment(mandate["mandate_id"], "agent:anchor-test", amount, payee)
    assert "error" not in auth, auth
    return mandate, auth


def test_anchor_then_verify(tmp_path):
    mandate, _ = _mandate_with_payment()
    anchor_file = tmp_path / "roots.jsonl"

    published = publish_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert published["status"] == "ANCHORED", published
    assert published["root"] != "GENESIS"
    assert published["anchor_hash"]

    check = verify_against_published_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert check["status"] == "VERIFIED", check
    print("Anchor + verify test PASSED")


def test_no_anchor():
    mandate, _ = _mandate_with_payment(payee="api:news")
    check = verify_against_published_root(
        mandate["mandate_id"], anchor_file=Path("definitely/not/here.jsonl")
    )
    assert check["error"] == "NO_ANCHOR"
    print("No-anchor test PASSED")


def test_modified_since_anchor(tmp_path):
    mandate, _ = _mandate_with_payment()
    anchor_file = tmp_path / "roots.jsonl"
    publish_root(mandate["mandate_id"], anchor_file=anchor_file)

    # Chain intact, but a NEW payment lands after the anchor
    late = authorize_payment(mandate["mandate_id"], "agent:anchor-test", 200, "api:news")
    assert "error" not in late

    check = verify_against_published_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert check["status"] == "MODIFIED_SINCE_ANCHOR", check
    assert check["current_length"] == check["anchored_length"] + 1
    print("Modified-since-anchor test PASSED")


def test_tampered_chain_detected(tmp_path):
    mandate, auth = _mandate_with_payment()
    anchor_file = tmp_path / "roots.jsonl"
    publish_root(mandate["mandate_id"], anchor_file=anchor_file)

    # Insider rewrites the amount directly in the store
    conn = _db()
    conn.execute("UPDATE payment_auths SET amount=99999 WHERE jti=?", (auth["jti"],))
    conn.commit()
    conn.close()

    check = verify_against_published_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert check["status"] == "CHAIN_BROKEN", check
    print("Tampered-chain detection test PASSED")


def test_re_anchor_flow(tmp_path):
    mandate, _ = _mandate_with_payment()
    anchor_file = tmp_path / "roots.jsonl"
    publish_root(mandate["mandate_id"], anchor_file=anchor_file)

    late = authorize_payment(mandate["mandate_id"], "agent:anchor-test", 200, "api:weather")
    assert "error" not in late

    # Audit signal pehle dikhta hai, phir re-anchor karke phir se VERIFIED
    signal = verify_against_published_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert signal["status"] == "MODIFIED_SINCE_ANCHOR"

    publish_root(mandate["mandate_id"], anchor_file=anchor_file)
    ok = verify_against_published_root(mandate["mandate_id"], anchor_file=anchor_file)
    assert ok["status"] == "VERIFIED"

    anchors = list_anchors(anchor_file=anchor_file)
    assert len(anchors) == 2
    assert anchors[-1]["length"] == 2
    print("Re-anchor flow test PASSED")


def test_unknown_mandate():
    result = compute_mandate_root("no-such-mandate-id")
    assert result["error"] == "MANDATE_NOT_FOUND"
    print("Unknown mandate test PASSED")
