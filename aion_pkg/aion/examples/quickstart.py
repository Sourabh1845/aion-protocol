"""Quickstart: give YOUR agent a trust layer in ~20 lines.

The pattern: wrap any dangerous agent action in a guard, and give the
agent a spending mandate. Everything dangerous becomes allow/block/
approval + a tamper-evident receipt.
"""


def main():
    # 1) The human sets hard limits (RSA-signed — the agent cannot exceed these)
    from aion.payments import create_intent_mandate

    mandate = create_intent_mandate(
        principal="user:me",
        agent="agent:my-first-agent",
        max_per_payment=500,          # max per payment (smallest currency unit)
        max_total=1000,               # max total budget
        payees=["api:weather"],       # allowlist — nothing else gets paid
    )
    assert "error" not in mandate, mandate
    print("mandate:", mandate["mandate_id"], "| signed:", bool(mandate["signature"]))

    # 2) Your agent wants to buy something -> ask AION, never trust the prompt
    from aion.payments import authorize_payment, settle_payment

    auth = authorize_payment(mandate["mandate_id"], "agent:my-first-agent", 300, "api:weather")
    assert "error" not in auth, auth
    print("one-time auth:", auth["jti"], "-> bound to 300 -> api:weather")

    # 3) After the real payment (x402 tx hash, or any settlement reference)
    settled = settle_payment(auth["jti"], "x402:tx_0xabc123")
    assert "error" not in settled, settled
    print("settled | receipt:", settled["receipt_hash"][:24], "...")

    # 4) Guard ANY dangerous action (not just payments) — decorator style
    from aion.guard import guard

    @guard(scope="shell.run", agent="agent:my-first-agent",
           metadata_factory=lambda command: {"command": command})
    def run_shell(command):
        return f"ran: {command}"

    try:
        run_shell("rm -rf important-stuff")     # blocked by pattern match
    except Exception as exc:
        print("guard blocked:", type(exc).__name__)

    # 5) Prove everything to a third party
    from aion.payments import export_dispute_bundle
    bundle = export_dispute_bundle(mandate["mandate_id"])
    print("dispute bundle:", bundle["bundle_type"], "| chain_intact:", bundle["chain_intact"])

    print("\nThat's the whole loop: limits -> one-time auth -> receipt -> proof.")
    print("Next: aion example langchain_agent  (plug into a real agent)")


if __name__ == "__main__":
    main()
