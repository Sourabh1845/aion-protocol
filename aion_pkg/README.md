# AION Protocol

**The trust layer for AI agents — identity, limits, and court-ready proof for every agent action.**

AI agents don't just chat anymore — they spend money, run code, delete files, and call other agents.
What they're missing is a bank-grade control layer. AION gives every agent:

- 🪪 **Identity** — a signed Intent Mandate (budget + payee allowlist + expiry) the agent cannot exceed
- 🚦 **Limits** — one-time, amount-and-payee-bound payment authorizations (replay-proof)
- 🧾 **Proof** — tamper-evident, hash-chained receipts for every action
- ⚖️ **Disputes** — exportable, third-party-verifiable evidence bundles

AION doesn't move money — rails like [x402](https://www.x402.org) do.
AION decides **whether a payment is allowed, and proves what happened.**

## Quickstart

```bash
pip install aion-protocol
```

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
pip install "aion-protocol[cloud]"
uvicorn aion.api:app
```

Endpoints: `/issue`, `/enforce`, `/verify/{jti}`, `/revoke/{jti}`, `/health`.
The server boots in degraded mode if the database is down and reports it in `/health`.

## Status

- Scan: ✅ | Guard: ✅ | Authority (one-time tokens + delegation): ✅
- Receipts + audit chain: ✅
- Payment Trust Rails (mandate → bound auth → settlement → dispute bundle): ✅
- x402 adapter: 🔜 | Hosted verification network: 🔜

## Links

- Landing page: https://sourabh1845.github.io/aion-protocol
- GitHub: https://github.com/Sourabh1845/aion-protocol
- Live API: https://aion-protocol.onrender.com

Built by Sourabh Ranjan Sahoo.

