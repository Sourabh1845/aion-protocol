# Reapplication answers (EverVent / Z-Fellows)

This file is a **template**. I do not have the original applications or the
current questions for either program, so the fields marked `TODO` need to be
filled from the program's actual form before submitting. The proof points and
the narrative below are accurate as of v2.3.2.

## The 30-second pitch (reuse verbatim)

> AION is the trust layer for AI agents: identity, limits, and court-ready proof
> for every agent action. An AI agent gets a signed mandate it cannot exceed,
> one-time payment authorizations bound to exact amount and payee, hash-chained
> receipts anchored outside the operator's control, and exportable dispute
> bundles. It does not move money - rails like x402 do; AION decides whether a
> payment is allowed and proves what happened. Shipped as `aion-core` on PyPI,
> MIT licensed, one dependency, 54 tests, CI on Python 3.10 and 3.12.

## What changed since the last application (the part reviewers weigh)

- Released **v2.1.0 -> v2.3.2** on PyPI, all verified live after upload.
- Payments layer: signed mandates, one-time bound authorizations, settlement
  binding, dispute bundles (`14/14` checks in `payments_demo.py`).
- **x402 adapter**: client pre-flight, seller-side verify, settlement binding
  (`8/8` checks in `x402_demo.py`). Attack cases blocked: overcharge, rogue
  payee, double-spend/replay, prompt-injected terms, agent mismatch.
- **External anchoring**: `aion anchor` / `aion anchor-verify` publish and check
  the chain root outside the operator's store, which is what turns
  "tamper-evident" into something a third party can verify.
- **First-5-minutes experience**: `aion demo` (offline, 60s), `aion doctor`,
  `aion example {quickstart,langchain_agent,crewai_agent}`, bundled runnable
  examples, and `INTEGRATION.md` for LangChain/LangGraph, CrewAI, MCP, plain Python.
- **Verification API live** in production (FastAPI + Postgres on Render) with
  `/issue`, `/enforce`, `/verify`, `/revoke`, `/health`; degraded-mode boot so the
  service stays up if the database is down.
- **Hardening this release**: auth fails closed (`AION_API_KEY` required, 503 if
  unset), no hardcoded keys anywhere in the repo, `SECURITY.md`, `THREAT_MODEL.md`,
  and `docs/COMPLIANCE_PITCH.md`.
- **CI green** on every push (Python 3.10 + 3.12).

## Reusable Q&A

**What is the problem you are solving?**
Agents act in the real world with no authority layer. A prompt is a suggestion,
and observability tools only tell you what already happened. AION answers two
questions in the code path: is this action allowed, and can we prove what
happened later - to a counterparty, an insurer, or a court.

**Why now?**
Agents went from chat to spending and shell access faster than any control layer
was built for. x402 and card rails solved moving money; nothing solved proving
that the human's intent was respected. That gap is what we fill.

**Why are you the person to build this?**
TODO: 2-3 lines on your background, the specific incident that made you
build it, and why you shipped it in public rather than keeping it internal.

**Traction / evidence to cite (all reproducible right now)**

- `pip install aion-core` -> `aion demo` blocks three live attacks (offline, no keys).
- 54 tests passing; CI green on 3.10 and 3.12; green pipeline link available.
- x402 adapter: `8/8` attack checks; payments: `14/14`; anchoring: `6/6`.
- Public threat model that names what is *not* provable.
- Live hosted verification API in production.

**Metrics to have ready (fill in your own numbers; do not guess)**

- PyPI downloads last 30 days: TODO
- GitHub stars / forks: TODO
- Users, design partners, or pilot conversations: TODO
- Community threads, inbound requests, or talks: TODO

**What is the biggest risk?**
Distribution, not technology. The protocol pieces work and are tested; whether
agent builders adopt an authorization layer before a regulator forces one is an
open question. The second risk is honestly scoped: an operator who controls the
store can rewrite an unanchored history, which is why external anchoring exists
and why the threat model says so out loud.

**What do you need from the program?**
TODO: pick from - intros to agent-platform teams or facilitators (x402/Coinbase,
LangChain, CrewAI), compliance/legal review time, and a small amount of compute
credit. Keep it to two or three concrete asks, not a wish list.

**Why not just build it as a feature inside an agent framework?**
Because the enforcement point must be outside the agent's runtime - the runtime
is exactly what gets prompt-injected. A framework shipping its own mandate check
is still a self-report. That is also why AION is framework-agnostic and why the
guard decorator works with anything callable.

**Open source or commercial?**
MIT today, everything in the open, including the parts that make us look worse
(see the threat model). Commercial path, if any, is the hosted verification
network and audit-grade evidence retention - not the enforcement primitives.

**Honest status**
Pre-revenue, one maintainer, no funding, no security audit. Every claim above is
reproducible from a fresh `pip install`. If a claim cannot be reproduced, treat it
as a bug and report it.

## Submission checklist

- [ ] Replace every `TODO` with a real answer.
- [ ] Attach the 5 proof screenshots from `04-rogue-agent-demo.md`.
- [ ] Attach or link the 45-60s demo recording.
- [ ] Link the green CI run and the PyPI page.
- [ ] Re-read the pitch once and remove any word you could not defend on a call.
- [ ] Confirm the hosted API key was rotated (see `README.md` step 1) before
      posting any public link to the repo.
