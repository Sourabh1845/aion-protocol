# Show HN

## Title options (pick one, keep under 80 chars)

1. `Show HN: AION – a trust layer for AI agents (limits, receipts, court-ready proof)`
2. `Show HN: Give your AI agent a spending mandate it cannot exceed`
3. `Show HN: I built the missing authorization layer for AI agent payments`

## Body

AI agents now spend money, delete files, run shell commands, and call other
agents. Almost everything we have for them is a prompt-level guardrail - which
is to say, a suggestion. I kept hitting the same gap: there is no *authority*
layer. Nothing a model cannot rewrite.

AION is that layer. It does not move money (x402 and card rails do). It decides
whether an action is allowed, and proves what happened:

```
pip install aion-core
aion demo        # whole story in 60 seconds, offline
```

What the demo does, in order:

1. A human signs an **Intent Mandate**: "agent:demo-bot may pay max 500 per
   payment, 1000 total, only to api:weather and api:news". RSA-signed. The
   agent's prompts can say anything; this signature wins.
2. The agent requests a **one-time authorization** bound to the exact amount and
   payee, expiring in 120 seconds.
3. It settles. The settlement reference (e.g. an x402 tx hash) is chained into a
   receipt.
4. Three live attacks get blocked: replay of a settled authorization
   (`ALREADY_SETTLED`), overspend (`AMOUNT_LIMIT`), and a prompt-injected rogue
   payee (`PAYEE_NOT_ALLOWED`).
5. The receipt chain is verified and its root is **anchored** outside the
   operator's store, then a **dispute bundle** (signatures + chain + anchors) is
   exported with a single `bundle_hash`.

Beyond payments, the same machinery covers arbitrary action scopes - file,
email, shell, secrets, deploy - via `@guard(scope=...)`: allow, block, or require
human approval, each decision producing a receipt.

Some things I deliberately did *not* hand-wave:

- A locally hash-chained log is tamper-**evident**, not tamper-proof - whoever
  holds the store can rewrite it. That is why `aion anchor` publishes the root
  somewhere the operator does not control (a git commit, a gist, an endpoint).
  `THREAT_MODEL.md` lists what is cryptographically verifiable versus operator-held.
- Auth fails closed. The hosted API requires `AION_API_KEY` and returns 503 if it
  is unset; there is no well-known default key.
- It is one maintainer, no funding, and no third-party security audit yet.

Tech: pure Python, only `cryptography` as a dependency; 54 tests; CI on 3.10 and
3.12. LangChain/LangGraph, CrewAI, MCP, or plain Python - `INTEGRATION.md` has
copy-paste starters, and `aion example quickstart` prints a runnable one.

Repo: https://github.com/Sourabh1845/aion-protocol

Feedback I would value most: (a) is "signed mandate + one-time bound auth +
anchored receipts" the right abstraction, or is it too much ceremony for agent
payments? (b) what is the strongest attack on this you can think of?

## First comment (post immediately after submitting)

Author here. A few implementation details that usually come up:

- **Why not just let the agent's framework enforce limits?** Because the agent's
  runtime is the thing that got prompt-injected. AION's decisions depend only on
  signatures and on state the agent cannot write to - not on the model's goodwill.
- **Why x402?** The x402 spec requires that funds move "in accordance with client
  intentions", but the protocol has no way to sign, bind, or prove those
  intentions. AION supplies that: a signed mandate the agent cannot exceed, plus
  settlement hashes chained into receipts. Overcharge, rogue payee, double-spend,
  and prompt-injected terms are all blocked in `aion demo`.
- **Is the receipt chain really tamper-proof?** No, and I will not claim it is.
  It is tamper-evident locally; it becomes third-party verifiable once you anchor
  the root somewhere you do not control. `aion anchor-verify` returns VERIFIED /
  MODIFIED_SINCE_ANCHOR / CHAIN_BROKEN.
- **What is not built yet?** No hosted multi-tenant PKI, no UI beyond the demo
  CLI, no EU AI Act / SOC2 mapping beyond `docs/COMPLIANCE_PITCH.md`, and no
  independent review.
- **Trying it takes one command:** `pip install aion-core && aion demo` (offline,
  no keys, no network).

## Reply bank (keep short, honest, non-defensive)

- "Another guardrail wrapper": the difference is the enforcement point. Nothing
  here runs inside the model's decision path; it is a signature check plus an
  append-only receipt, verifiable by a third party.
- "Blockchain would be better": anchoring is engine-agnostic - today a git commit
  or any endpoint you control. If you want a chain, publish the root there.
- "Will you support `<framework>`?": the SDK is framework-agnostic; the guard
  decorator wraps any function. Framework examples exist for LangChain and CrewAI,
  and PRs for others are welcome.
- "How is this different from `<agent observability tool>`?": observability
  records what happened. This decides what is *allowed* before it happens, then
  ties the record to the authorization.
