# Give your AI agent AION in 5 minutes

Whichever framework you use, the pattern is the same:

1. **Wrap dangerous actions** with `@guard(...)` — allow/block/approval + receipts
2. **Route payments** through a signed mandate — one-time, bounded auths
3. **Prove history** with receipts, chains, anchors, dispute bundles

---

## Install

```bash
pip install aion-core
aion doctor        # verify your install (5 seconds)
aion demo          # see the whole trust layer in 60 seconds
```

---

## 1. Plain Python (any agent, any framework)

```python
from aion.guard import guard
from aion.payments import (
    authorize_payment, create_intent_mandate, export_dispute_bundle, settle_payment,
)

# Human signs the mandate — the agent's ONLY real power
mandate = create_intent_mandate(
    principal="user:me",
    agent="agent:my-agent",
    max_per_payment=500,
    max_total=1000,
    payees=["api:weather"],
)

# Any dangerous action: wrap it
@guard(scope="file.delete", agent="agent:my-agent",
       metadata_factory=lambda path: {"path": path})
def delete_file(path):
    ...  # only runs if policy allows (or human approves)

# Any payment: never trust the prompt, ask AION
auth = authorize_payment(mandate["mandate_id"], "agent:my-agent", 300, "api:weather")
if "error" not in auth:
    settle_payment(auth["jti"], "x402:tx_abc123")     # real settlement reference

# Prove it later
bundle = export_dispute_bundle(mandate["mandate_id"])  # signatures + chain + anchors
```

Full runnable version: `aion example quickstart`

---

## 2. LangChain / LangGraph

```python
from langchain_core.tools import tool
from aion.guard import guard

@tool
@guard(scope="shell.run", agent="agent:langchain-agent",
       metadata_factory=lambda command: {"command": command})
def run_shell(command: str) -> str:
    """Run a shell command (guarded)."""
    return f"ran: {command}"
```

That's it — blocked/approval actions raise before your tool body runs,
and every call leaves a receipt. Payments: wrap your pay-tool's body with
`authorize_payment(...)` as shown in the full example.

Full runnable version: `aion example langchain_agent`

---

## 3. CrewAI

```python
from crewai.tools import BaseTool
from aion.guard import guard

class ShellTool(BaseTool):
    name: str = "run_shell"
    description: str = "Run a shell command (AION-guarded)"

    def _run(self, command: str) -> str:
        @guard(scope="shell.run", agent="agent:crewai-agent",
               metadata_factory=lambda cmd: {"command": cmd})
        def guarded(cmd):
            return f"ran: {cmd}"
        return guarded(command)
```

Full runnable version (incl. pydantic `args_schema` for multi-arg tools):
`aion example crewai_agent`

---

## 4. MCP servers / raw HTTP agents

Expose AION as tools your MCP server can call:

- `aion.issue(scope)` / `aion.enforce(jti, scope)` — one-time action tokens
- `aion.authorize_payment(mandate_id, agent, amount, payee)` — bounded payment auth
- `aion.x402.authorize_x402(mandate_id, requirements)` — pre-flight real x402 offers

Or run the hosted API and call it over HTTP:

```bash
pip install "aion-core[cloud]"
uvicorn aion.api:app   # /issue /enforce /verify/{jti} /revoke/{jti} /health
```

---

## 5. x402 agents (pay-per-call APIs)

If your agent hits 402-paywalled APIs (x402 standard):

```python
from aion import x402

# seller's PAYMENT-REQUIRED body arrives → pre-flight it against the mandate
decision = x402.authorize_x402(mandate_id, payment_required_body)
if decision["decision"] == "allow":
    # sign & send the real x402 payment, carrying decision["aion_jti"]
    ...
# after the facilitator settles — bind the on-chain proof into your receipt chain
x402.settle_x402(decision["aion_jti"], payment_response)
```

Full runnable version: `aion example quickstart` + README's x402 section.

---

## Customize the rules

`aion policy-init` creates `aion-policy.json` — decide per-scope:
`allow` / `log` / `approval` (human-in-the-loop) / `block`, plus
`block_patterns` (e.g. `rm -rf`) and wildcards (`secrets.*`).

## Verify it all

```bash
aion receipts 10            # action history
aion pay-chain <mandate>    # chain integrity
aion anchor <mandate>       # publish root externally (git = compliance ledger)
aion anchor-verify <mandate>
aion dispute <mandate> --save   # court-ready bundle
```

See [THREAT_MODEL.md](THREAT_MODEL.md) for exactly what is
cryptographically verifiable vs operator-held.
