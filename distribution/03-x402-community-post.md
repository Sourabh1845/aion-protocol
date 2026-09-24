# x402 community post

Target: x402 GitHub Discussions ("Show and tell" / "Ideas"), x402 Discord
`#builders`, and any x402-related Spaces/threads. Adjust tone per venue - the
version below is for GitHub Discussions.

---

**Title:** AION - a signed-intent / mandate layer for x402 payments (open source, MIT)

Hey all. I have been building on x402 and kept running into the same gap, so I
want to put it in front of people who know the protocol better than I do.

The x402 spec is explicit that funds must only move in accordance with client
intentions. What the protocol gives us on the wire is a payment requirement
(amount, payee, asset, network) and a settlement proof. What it does not give us
is a way for the *client* to sign, bound, and prove their intentions - so today
"in accordance with client intentions" is enforced by whatever the agent process
happens to do.

AION is a small library that adds that missing layer. It does not move money and
it does not replace a facilitator; it sits between your agent and the rail:

```python
from aion.payments import create_intent_mandate, authorize_payment, settle_payment

mandate = create_intent_mandate(
    principal="user:me", agent="agent:shopbot",
    max_per_payment=5, max_total=25, payees=["api:weather", "api:news"],
)
auth = authorize_payment(mandate["mandate_id"], "agent:shopbot", 0.003, "api:weather")
# -> one-time authorization bound to this exact amount + payee, expires in 120s
settle_payment(auth["jti"], "x402:tx_0xabc123")   # settlement hash enters the receipt chain
```

For the seller side there is a check you can call inside `/verify`: given the
mandate id, the 402 requirements body, and the jti, it returns whether the
payment is actually authorized (`aion x402-check`). There is also an adapter for
the client pre-flight (`aion x402-pay`) and settlement binding
(`aion x402-settle`), plus a runnable demo (`python x402_demo.py`, 8/8 checks).

Attack cases that get blocked, with codes:

| Case | Result |
|---|---|
| seller overcharges vs the mandate | `AMOUNT_LIMIT` |
| payee swapped / rogue payee | `PAYEE_NOT_ALLOWED` |
| replay of a settled authorization (double-spend) | `ALREADY_SETTLED` |
| prompt-injected terms differ from what the human signed | `INVALID_SIGNATURE` |
| different agent presents the authorization | `AGENT_MISMATCH` |

Two things I would genuinely like feedback on from x402 folks:

1. **Scoping.** Is a signed mandate keyed by `(agent, payee allowlist, per-payment
   cap, total cap, expiry)` the right primitive, or would the ecosystem rather
   see this expressed inside the 402 response itself (e.g. a `mandate` proof the
   client echoes back)?
2. **Settlement binding.** I chain the settlement reference (facilitator tx hash
   or off-chain reference) into the receipt chain. Is there a canonical field in
   the x402 response that should be used as the verifiable settlement identifier?
   If there is a better place to pin the digest, I will change it.

Also happy to be told this belongs outside x402 core entirely and should stay a
sidecar library - that is a completely reasonable answer.

Repo: https://github.com/Sourabh1845/aion-protocol
Install: `pip install aion-core` (then `aion demo` - offline, no keys)
Threat model (what is and is not cryptographically provable):
https://github.com/Sourabh1845/aion-protocol/blob/main/THREAT_MODEL.md

---

## Short variant for Discord

Built a signed-intent (mandate) layer for x402 - it adds what the spec assumes
but does not encode: a human-signed spending mandate the agent cannot exceed,
one-time authorizations bound to exact amount + payee, and settlement hashes
chained into tamper-evident receipts. Sellers get a `check` call for `/verify`.
Overcharge, rogue payee, double-spend and prompt-injected terms are all blocked.

`pip install aion-core && aion demo` (offline, 60s). MIT.

Curious whether people think this belongs in x402 core or as a sidecar - and
where the right field is to pin the settlement digest.
