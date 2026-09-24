"""LangChain integration: give a LangChain agent AION guardrails.

Requires: pip install langchain-core

The pattern is tiny - wrap your tool functions with @guard. Blocked or
approval-required actions raise before your tool ever runs, and every
call leaves a tamper-evident receipt.
"""


def main():
    pytest_skip = None
    try:
        from langchain_core.tools import tool
    except ImportError:
        print("This example needs langchain-core:")
        print("    pip install langchain-core")
        return

    # --- AION imports -------------------------------------------------
    from aion.guard import guard
    from aion.payments import authorize_payment, create_intent_mandate, settle_payment

    # --- 1) A spending mandate for this agent ------------------------
    mandate = create_intent_mandate(
        principal="user:me",
        agent="agent:langchain-demo",
        max_per_payment=500,
        max_total=1000,
        payees=["api:weather"],
    )
    print("mandate:", mandate["mandate_id"])

    # --- 2) A guarded LangChain tool: shell access -------------------
    @tool
    @guard(scope="shell.run", agent="agent:langchain-demo",
           metadata_factory=lambda command: {"command": command})
    def run_shell(command: str) -> str:
        """Run a shell command (guarded by AION - rm -rf style patterns are blocked)."""
        return f"ran: {command}"

    try:
        print(run_shell.invoke({"command": "rm -rf critical"}))
    except Exception as exc:
        print("AION blocked the tool call:", type(exc).__name__)

    # --- 3) A payment tool that cannot overspend ---------------------
    @tool
    def pay_api(payee: str, amount: int) -> dict:
        """Pay an API under the human's signed mandate (one-time auth + settlement)."""
        auth = authorize_payment(mandate["mandate_id"], "agent:langchain-demo", amount, payee)
        if "error" in auth:
            return {"blocked": auth["error"]}
        settle = settle_payment(auth["jti"], f"x402:tx_demo_{auth['jti'][:8]}")
        return {"settled": settle.get("status"), "receipt": settle.get("receipt_hash", "")[:16]}

    print(pay_api.invoke({"payee": "api:weather", "amount": 300}))   # allowed
    print(pay_api.invoke({"payee": "api:sketchy", "amount": 300}))   # PAYEE_NOT_ALLOWED

    print("\nYour LangChain agent now runs under human-signed limits,")
    print("and every call left a court-ready receipt.")


if __name__ == "__main__":
    main()
