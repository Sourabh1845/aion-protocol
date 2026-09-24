# Rogue agent demo - recording script

Goal: a 45-60s clip that makes the thesis land without narration tricks. Two
versions below: **A (offline, recommended for HN/X)** and **B (adversarial suite
against the hosted API)**. Keep the terminal font large (18pt+) and hide the
prompt clutter.

## Pre-flight (do this 10 minutes before recording)

```powershell
# 1) Warm the free Render instance so it is not cold-starting on camera
curl.exe -s https://aion-protocol.onrender.com/health

# 2) Fresh shell, clean state so the demo prints the real thing
aion doctor
```

If `aion doctor` shows two `[OPTIONAL]` lines for LangChain/CrewAI that is fine -
that is intentional (optional integrations, not failures).

## Version A - offline, 45 seconds (use this one)

| Time | Command | What the viewer sees |
|---|---|---|
| 0:00 | `pip install aion-core` | one dependency, no keys |
| 0:06 | `aion demo` | the whole story starts |
| 0:10 | *(rolls itself)* | mandate signed: max 500/payment, 1000 total, 2 payees |
| 0:18 | *(rolls)* | one-time auth bound to exact amount + payee |
| 0:22 | *(rolls)* | `SETTLED` + receipt hash |
| 0:27 | *(rolls)* | ATTACK: replay -> `BLOCKED -> ALREADY_SETTLED` |
| 0:31 | *(rolls)* | ATTACK: overspend -> `BLOCKED -> AMOUNT_LIMIT` |
| 0:35 | *(rolls)* | ATTACK: rogue payee -> `BLOCKED -> PAYEE_NOT_ALLOWED` |
| 0:39 | *(rolls)* | chain intact, root anchored, independent check `VERIFIED` |
| 0:44 | *(rolls)* | dispute bundle with one `bundle_hash` |

Caption over the three BLOCKED lines: **"The agent's prompts can say anything.
The signature wins."**

Closing card (2s): `pip install aion-core` · github.com/Sourabh1845/aion-protocol

## Version B - adversarial suite against the hosted API (for the technical cut)

Only if you want the "real server, real network" version. These scripts now
require a key you set yourself (nothing is hardcoded):

```powershell
$env:AION_API_KEY = '<your-key>'
$env:GROQ_API_KEY = '<your-groq-key>'      # only for autonomous_rogue_test.py
python rogue_agent_test.py                 # auth + replay + tamper suite
python autonomous_rogue_test.py            # LLM agent tries malicious actions, AION blocks each
python tamper_test.py                      # modified jti -> rejected
python concurrent_test.py                  # 50 parallel enforces -> exactly one wins
python x402_demo.py                        # 8/8 x402 attack checks
```

Screenshot the pass lines only; do not show the key. If a run fails because the
free instance is cold, re-run once before recording.

## Beats for the voiceover (or on-screen text)

1. "Your agent has your card and your shell. Its guardrail is a prompt."
2. "So the human signs limits the agent cannot change."
3. "Every payment is one-time, amount-bound, payee-bound."
4. "Watch three attacks die."
5. "Then the receipt chain is anchored somewhere the operator does not control -
   so tampering is detectable by a third party, not just by me."
6. "Math, not trust. `pip install aion-core`."

## Description / post copy for the upload

> An AI agent gets a signed spending mandate it cannot exceed: max 500 per
> payment, 1000 total, two allowed payees. Three live attacks - replay,
> overspend, prompt-injected rogue payee - are blocked, then the receipt chain is
> anchored and a court-ready dispute bundle is exported.
>
> AION is the trust layer for AI agents: identity, limits, and court-ready proof.
> It does not move money - x402 and card rails do. It decides whether an action
> is allowed and proves what happened. MIT, Python, one dependency.
>
> pip install aion-core
> https://github.com/Sourabh1845/aion-protocol

## Things that must NOT be claimed on camera or in the caption

- Not "tamper-proof" - tamper-evident, unless the root is anchored outside the
  operator's store.
- Not "audited", "bank-grade", or "compliant" - there is no third-party review,
  and compliance mapping is a positioning document (`docs/COMPLIANCE_PITCH.md`).
- Not "the agent cannot do X" - say "AION blocks X", because enforcement lives in
  the code path that calls AION, not in the model.
- No customer names, no revenue numbers, no logos you do not have permission to use.

## Reusable proof screenshots (capture once, reuse in the reapplication form)

1. `aion doctor` -> `HEALTHY - AION is ready.`
2. `aion demo` -> the three `BLOCKED ->` lines + `VERIFIED` anchor check.
3. `python x402_demo.py` -> `8/8` pass summary.
4. `python payments_demo.py` -> `14/14` pass summary.
5. GitHub Actions -> green CI run on 3.10 and 3.12.
6. PyPI page for `aion-core` showing the current version.
