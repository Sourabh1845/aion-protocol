# AION Protocol

[![tests](https://github.com/Sourabh1845/aion-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/Sourabh1845/aion-protocol/actions/workflows/ci.yml)

**The trust layer for AI agents — identity, limits, and court-ready proof for every agent action.**

AI agents don't just chat anymore — they spend money, run code, delete files, and call other agents.
What they're missing is a bank-grade control layer. AION gives every agent:

- 🪪 **Identity** — a signed Intent Mandate (budget + payee allowlist + expiry) the agent cannot exceed
- 🚦 **Limits** — one-time, amount-and-payee-bound payment authorizations (replay-proof)
- 🧾 **Proof** — hash-chained receipts, externally anchorable, secrets auto-redacted
- ⚖️ **Disputes** — exportable, third-party-verifiable evidence bundles (math, not trust)

AION doesn't move money — rails like [x402](https://www.x402.org) do.
AION decides **whether a payment is allowed, and proves what happened.**

## Quickstart

```bash
pip install aion-core
aion doctor        # verify your install (5 seconds)
aion demo          # see the whole trust layer in 60 seconds
```

**Wire it into your agent:** [INTEGRATION.md](../INTEGRATION.md) — LangChain, CrewAI,
MCP, or plain Python. Runnable starters: `aion example quickstart` (and
`langchain_agent`, `crewai_agent`).

> **Package name note:** AION ships as **`aion-core`** on PyPI (v2.1+).
> The older `aion-protocol` package (v2.0.0) predates the Payment Trust Rails
> and x402 adapter — use `aion-core` for the full trust layer.

**1. Scan** — find risky patterns in your agent's code:

```bash
aion scan .
```

**2. Guard** — allow, block, or require approval for actions:

```bash
aion guard-demo
```

**3. Payments** — give your agent a spending mandate and let it pay safely:

```bash
# Create a signed mandate: agent:shopbot can spend max 500/payment, 1000 total, only these payees
aion mandate-create agent:shopbot 500 1000 "api:weather,api:news"

# Agent requests a one-time payment auth (bound to exact amount + payee)
aion pay <mandate_id> 300 api:weather

# Settle it with the on-chain/off-chain reference
aion settle <jti> x402:tx_0xabc123

# Verify as a third party / export court-ready dispute evidence
aion pay-verify <jti>
aion dispute <mandate_id> --save
```

Attack table (all enforced, all tested):

| Attack | AION response |
|---|---|
| Replay a settled payment | `ALREADY_SETTLED` |
| Spend over per-payment limit | `AMOUNT_LIMIT` |
| Spend over total budget (race-safe) | `BUDGET_EXHAUSTED` |
| Pay an unapproved payee | `PAYEE_NOT_ALLOWED` |
| Tamper with stored payment terms | `INVALID_SIGNATURE` |
| Tamper with the receipt chain | `chain_intact: false` |
| Rogue sub-agent | `AGENT_MISMATCH` |

**4. x402 adapter** — enforce the human's intent on real [x402](https://www.x402.org) payments:

```bash
# Seller asks for 0.003 USDC on base-sepolia (x402 PAYMENT-REQUIRED body)
# Agent pre-flights it: does the signed mandate allow this exact payment?
aion x402-pay <mandate_id> @x402-requirements.json

# Seller-side: is this agent's payment actually allowed? (called inside /verify)
aion x402-check <mandate_id> @x402-requirements.json <jti>

# Bind the on-chain settlement hash into the receipt chain
aion x402-settle <jti> @x402-response.json
```

x402's own spec says funds **"must only move in accordance with client intentions"** —
but the protocol has no way to sign, bind, or prove those intentions. AION adds that
missing layer: a signed mandate the agent cannot exceed, one-time authorizations bound
to exact amount + payee, and settlement hashes chained into verifiable receipts.
Overcharge, rogue payee, double-spend, and prompt-injected terms are all blocked.

## External anchoring — evidence a third party can trust

A locally hash-chained history is tamper-**evident**, but the operator still
holds the store. Anchoring closes that gap: publish the chain's root to a
place you don't control (a git repo, a gist, a cloud endpoint) and anyone can
later prove the history is intact — or that it was modified:

```bash
aion anchor <mandate_id>        # publish current root to .aion/anchors/roots.jsonl
aion anchor-verify <mandate_id> # VERIFIED / MODIFIED_SINCE_ANCHOR / CHAIN_BROKEN
aion anchors                    # list the published-root ledger
```

Commit `roots.jsonl` to git — the commit history becomes your append-only
compliance ledger. See [THREAT_MODEL.md](../THREAT_MODEL.md) for exactly what
is cryptographically verifiable vs operator-held, and the full attack table.

## Why not just trust the model?

A modern model writes clean code — that was never the problem.
The problem is **authority**: an agent that can act on the real world needs
the same thing humans got from banks: card limits, one-time OTPs, receipts,
and chargebacks. AION is that layer. It doesn't depend on the agent's
goodwill — only on signatures and state the agent cannot touch.

## Receipts

Every allowed/blocked/approved action gets a tamper-evident receipt
(sha256-chained, secrets auto-redacted):

```bash
aion receipts 10
```

## Optional: hosted verification API

Local mandates and receipts are free and offline. For third-party
verification, revocation, and cross-company agent trust, run the API server:

```bash
pip install "aion-core[cloud]"
uvicorn aion.api:app
```

Endpoints: `/issue`, `/enforce`, `/verify/{jti}`, `/revoke/{jti}`, `/health`.
The server boots in degraded mode if the database is down and reports it in `/health`.

## Status

- Scan: ✅ | Guard: ✅ | Authority (one-time tokens + delegation): ✅
- Receipts + audit chain: ✅
- Payment Trust Rails (mandate → bound auth → settlement → dispute bundle): ✅
- x402 adapter (client pre-flight, seller-side verify, settlement binding): ✅
- External chain-root anchoring (`anchor` / `anchor-verify`): ✅
- CI (Python 3.10 + 3.12, full suite on every push): ✅
- Hosted verification network: 🟡 live at https://aion-protocol.onrender.com

## Links

- Landing page: https://sourabh1845.github.io/aion-protocol
- GitHub: https://github.com/Sourabh1845/aion-protocol
- Live API: https://aion-protocol.onrender.com
- Threat model: [THREAT_MODEL.md](../THREAT_MODEL.md)
- Compliance positioning: [docs/COMPLIANCE_PITCH.md](../docs/COMPLIANCE_PITCH.md)

Built by Sourabh Ranjan Sahoo.

