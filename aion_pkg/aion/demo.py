"""`aion demo` — the 60-second AION story, end to end.

One command that shows a buyer what the trust layer actually does:
create a signed mandate, authorize a one-time payment, settle it, then
watch three live attacks get blocked, verify the chain, anchor it, and
export a court-ready dispute bundle.

Run:  aion demo
"""

from aion.anchoring import publish_root, verify_against_published_root
from aion.payments import (
    authorize_payment,
    create_intent_mandate,
    export_dispute_bundle,
    settle_payment,
    verify_payment_chain,
)


def _step(title):
    print(f"\n{'=' * 62}\n  {title}\n{'=' * 62}")


def run_demo():
    print("\nAION DEMO — trust layer for AI agents, in 60 seconds")
    print("(everything below runs on YOUR machine — no network, no cloud)")

    _step("1. The human signs a mandate (the agent's ONLY real power)")
    print('   "demo-bot may pay max 500 per payment, 1000 total,')
    print('    only to api:weather and api:news"')
    mandate = create_intent_mandate(
        principal="user:you",
        agent="agent:demo-bot",
        max_per_payment=500,
        max_total=1000,
        payees=["api:weather", "api:news"],
    )
    if "error" in mandate:
        print(f"   FAILED: {mandate}")
        return {"ok": False, "step": "mandate"}
    print(f"   mandate_id : {mandate['mandate_id']}")
    print(f"   RSA-signed : {mandate['signature'][:44]}...")
    print("   The agent's prompts can say anything. This signature wins.")

    _step("2. The agent pays legitimately (300 to api:weather)")
    auth = authorize_payment(mandate["mandate_id"], "agent:demo-bot", 300, "api:weather")
    if "error" in auth:
        print(f"   FAILED: {auth}")
        return {"ok": False, "step": "authorize"}
    print(f"   one-time auth: {auth['jti']}")
    print("   bound to EXACT amount + payee, expires in 120s")

    _step("3. Settlement — on-chain proof enters the receipt chain")
    result = settle_payment(auth["jti"], "x402:demo_tx_0xabc123")
    if "error" in result:
        print(f"   FAILED: {result}")
        return {"ok": False, "step": "settle"}
    print(f"   SETTLED | receipt: {result['receipt_hash'][:24]}...")

    _step("4. ATTACK — seller replays the same settled auth (double-spend)")
    replay = settle_payment(auth["jti"], "x402:demo_tx_attack")
    print(f"   AION: BLOCKED -> {replay['error']}")

    _step("5. ATTACK — agent tries to overspend (900 > 500 per-payment cap)")
    over = authorize_payment(mandate["mandate_id"], "agent:demo-bot", 900, "api:weather")
    print(f"   AION: BLOCKED -> {over['error']}")

    _step("6. ATTACK — prompt-injected agent pays a rogue payee")
    rogue = authorize_payment(mandate["mandate_id"], "agent:demo-bot", 100, "api:sketchy-shop")
    print(f"   AION: BLOCKED -> {rogue['error']}")

    _step("7. Chain integrity + external anchor")
    intact = verify_payment_chain(mandate["mandate_id"])
    print(f"   chain intact: {intact}")
    published = publish_root(mandate["mandate_id"])
    print(f"   root published: {str(published.get('root'))[:24]}...")
    verdict = verify_against_published_root(mandate["mandate_id"])
    print(f"   independent check: {verdict['status']}")
    if verdict["status"] != "VERIFIED":
        return {"ok": False, "step": "anchor"}

    _step("8. Dispute bundle — what you hand to a court/insurer/counterparty")
    bundle = export_dispute_bundle(mandate["mandate_id"])
    print(f"   bundle: {bundle['bundle_type']} | chain_intact: {bundle['chain_intact']}")
    print(f"   authorized: {bundle['total_authorized']} | settled: {bundle['total_settled']}")
    print(f"   bundle_hash: {bundle['bundle_hash'][:32]}...")

    print(f"\n{'=' * 62}")
    print("THE END — and only ~15 lines of your code were AION's.")
    print("\nYour turn:")
    print("  aion doctor            # verify your install")
    print("  aion example quickstart  # copy-paste SDK starter")
    print("  aion example langchain_agent  # plug into LangChain")
    print("  docs: https://github.com/Sourabh1845/aion-protocol")
    print(f"{'=' * 62}\n")

    return {
        "ok": True,
        "mandate_id": mandate["mandate_id"],
        "attacks_blocked": 3,
        "chain_intact": True,
        "anchor": verdict["status"],
        "bundle_hash": bundle["bundle_hash"],
    }


if __name__ == "__main__":
    run_demo()
