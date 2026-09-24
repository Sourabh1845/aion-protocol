"""CrewAI integration: guard an entire crew's tools with AION.

Requires: pip install crewai

Same pattern as LangChain — wrap tool logic with @guard and route
payments through a signed mandate. CrewAI BaseTool subclasses get the
same protection by calling guard-wrapped functions inside _run().
"""


def main():
    try:
        from crewai.tools import BaseTool
    except ImportError:
        print("This example needs crewai:")
        print("    pip install crewai")
        return

    from aion.guard import guard
    from aion.payments import authorize_payment, create_intent_mandate, settle_payment

    mandate = create_intent_mandate(
        principal="user:me",
        agent="agent:crewai-demo",
        max_per_payment=500,
        max_total=1000,
        payees=["api:weather"],
    )
    print("mandate:", mandate["mandate_id"])

    from pydantic import BaseModel, Field

    class PayInput(BaseModel):
        payee: str = Field(description="Payee identifier, e.g. api:weather")
        amount: int = Field(description="Amount in the smallest currency unit")

    class ShellTool(BaseTool):
        name: str = "run_shell"
        description: str = "Run a shell command (AION-guarded)"

        def _run(self, command: str) -> str:
            @guard(scope="shell.run", agent="agent:crewai-demo",
                   metadata_factory=lambda cmd: {"command": cmd})
            def guarded(cmd):
                return f"ran: {cmd}"

            return guarded(command)

    class PayTool(BaseTool):
        name: str = "pay_api"
        description: str = "Pay an API under the human's signed mandate"
        args_schema: type[BaseModel] = PayInput

        def _run(self, payee: str, amount: int) -> str:
            auth = authorize_payment(mandate["mandate_id"], "agent:crewai-demo", amount, payee)
            if "error" in auth:
                return f"BLOCKED: {auth['error']}"
            settle = settle_payment(auth["jti"], f"x402:tx_demo_{auth['jti'][:8]}")
            return f"settled: {settle.get('status')} receipt: {str(settle.get('receipt_hash'))[:16]}"

    shell = ShellTool()
    pay = PayTool()

    try:
        print(shell.run(command="rm -rf critical"))
    except Exception as exc:
        print("AION blocked:", type(exc).__name__)

    print(pay.run(payee="api:weather", amount=300))   # allowed
    print(pay.run(payee="api:sketchy", amount=300))   # blocked

    print("\nThe whole crew now operates inside human-signed limits.")


if __name__ == "__main__":
    main()
