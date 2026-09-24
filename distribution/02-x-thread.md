# X / Twitter thread

Post as a thread. Attach the 30-60s `aion demo` recording to tweet 1.

---

**1/**
Your AI agent has your card, your shell, and your inbox.

Its only guardrail is a prompt.

I built the layer that decides what an agent is *allowed* to do - and proves what it did.

`pip install aion-core`

*(attach recording)*

---

**2/**
Agents don't have an intelligence problem. They have an authority problem.

A model writes clean code - that was never the issue. The issue is that nothing stops it from spending 900 when the human authorized 500.

---

**3/**
So the human signs a mandate (RSA-signed):

"agent:demo-bot may pay max 500 per payment, 1000 total, only to api:weather and api:news"

That signature is the agent's only real power. Prompts can say anything; this wins.

---

**4/**
The agent then gets a one-time authorization, bound to the EXACT amount and payee, expiring in 120 seconds.

Not a cookie. Not a session. A single-use, amount-bound, payee-bound credential.

---

**5/**
Now the attacks. All of these are in `aion demo`, all tested:

- replay a settled payment -> ALREADY_SETTLED
- overcharge -> AMOUNT_LIMIT
- prompt-injected rogue payee -> PAYEE_NOT_ALLOWED
- tamper with the stored terms -> INVALID_SIGNATURE
- tamper with the receipt chain -> chain_intact: false
- rogue sub-agent -> AGENT_MISMATCH

---

**6/**
Every allowed/blocked decision becomes a hash-chained receipt with secrets redacted.

Then `aion anchor` publishes the chain root somewhere the operator does NOT control - a git commit, a gist, an endpoint.

Now a third party can prove the history was not rewritten. That is the whole trick.

---

**7/**
What you hand to a court, an insurer, or a counterparty: a dispute bundle.

Signatures + chain + anchors + totals, one `bundle_hash`.

Math, not trust.

---

**8/**
Honest limits, before someone else points them out:

- AION does not move money. x402 and card rails do. AION decides if it's allowed and proves what happened.
- An unanchored local chain is tamper-EVIDENT, not tamper-proof. Whoever holds the store can rewrite it.
- One maintainer, no funding, no audit yet.

---

**9/**
Extras people keep asking for: /9

- Works for any scope, not just payments - file, email, shell, secrets, deploy - via `@guard(scope=...)`.
- LangChain, CrewAI, MCP, or plain Python: `INTEGRATION.md` has copy-paste starters.
- 54 tests, CI on 3.10 + 3.12, one dependency (`cryptography`).

---

**10/**
Try it in 60 seconds, offline, no keys:

`pip install aion-core`
`aion doctor`
`aion demo`

Repo: https://github.com/Sourabh1845/aion-protocol
Landing: https://sourabh1845.github.io/aion-protocol

Tell me the strongest attack you can think of. I'll answer every one.

---

## Short single-post variant (if you prefer one tweet)

The trust layer for AI agents:

- signed spending mandate the agent cannot exceed
- one-time payment auths bound to exact amount + payee
- hash-chained receipts, externally anchorable
- court-ready dispute bundles

`pip install aion-core && aion demo`

60 seconds, offline, three live attacks blocked.
