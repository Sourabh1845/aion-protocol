# AION Threat Model

Public, versioned threat model for the AION trust layer.
Status: **v1 — September 2026**. This document is a living security artifact:
every claim maps to an enforced control and a test in the repository.

---

## 1. What AION protects (assets)

| Asset | Description |
|---|---|
| Principal's budget | The human's money, bounded by a signed Intent Mandate |
| Authorization integrity | One-time payment auths bound to exact amount + payee |
| Action history | Hash-chained receipts/audit log — the evidence trail |
| Delegation boundary | Sub-agents can never hold a wider scope than their parent |
| Revocation authority | The principal's ability to instantly kill a mandate |

## 2. Trust boundaries (read this before trusting the marketing)

**Cryptographically verifiable by a third party** (signatures + recomputable hashes):

- Mandate terms (RSA-2048/PSS signed at issue time)
- Payment auth terms (signed, bound to `amount + payee + currency` via binding hash)
- Chain linkage *between* receipts/payment records (each record's hash includes the previous one)
- **Externally anchored chain roots** (`aion anchor` publishes `{root, length}` to a JSONL
  ledger meant for git/other operator-independent storage; `aion anchor-verify` recomputes)

**Operator-held, NOT independently verifiable** (be honest with auditors about this):

- The SQLite/Postgres store itself — an insider with DB write access can attempt a full
  rewrite. Chain linkage makes partial tampering detectable; *external anchoring* is what
  makes it provable (a rewritten chain will no longer match a published root).
- The RSA private key lives on disk (`storage/` or `/etc/secrets` on Render).
  Compromise of the host = compromise of the signing key.
- Timestamps are host clocks (30s skew tolerated). No RFC-3161 trusted timestamps yet.
- The hosted API (aion-protocol.onrender.com) is a convenience, not a trust root.

## 3. Adversaries and enforced responses

| # | Adversary / attack | Enforced response | Test |
|---|---|---|---|
| 1 | Agent replays a settled payment auth | `ALREADY_SETTLED` | `test_replay_settlement_blocked` |
| 2 | Agent exceeds per-payment cap | `AMOUNT_LIMIT` | `test_per_payment_limit` |
| 3 | Agent drains total budget (incl. concurrent race) | Atomic SQL guard → `BUDGET_EXHAUSTED` | `test_budget_exhausted`, `concurrent_test.py` |
| 4 | Agent pays an unapproved payee | `PAYEE_NOT_ALLOWED` | `test_payee_allowlist` |
| 5 | Attacker edits stored payment terms (amount swap) | Signature check → `INVALID_SIGNATURE` | `test_tampered_terms_detected` |
| 6 | Attacker edits the chain / receipt data | Recomputed chain hash mismatch → `chain_intact: false` | `test_tampered_terms_detected`, `test_chain_verification_intact` |
| 7 | Insider rewrites the whole store | External anchor comparison → `MODIFIED_SINCE_ANCHOR` / `CHAIN_BROKEN` | `test_tampered_chain_detected`, `test_modified_since_anchor` |
| 8 | Rogue sub-agent requests payments | `AGENT_MISMATCH`; delegation keeps child scope ⊆ parent | `test_agent_mismatch`, delegation tests |
| 9 | x402 seller inflates amount / swaps payee after auth | Binding re-check → `BINDING_MISMATCH`, `PAYEE_MISMATCH`, `AMOUNT_MISMATCH` | `test_x402.py` |
| 10 | x402 seller settles the same auth twice | `AUTH_ALREADY_SETTLED` (replay at seller side) | `test_x402.py` |
| 11 | Secrets leak into evidence | Receipt metadata auto-redacts `secret/token/password/api_key` fields | `receipts.py`, `test_receipts` |
| 12 | Stolen mandate used later | TTL expiry (`MANDATE_EXPIRED`, `AUTH_EXPIRED`) + instant `revoke` | `test_payments.py`, CLI |

## 4. Known limitations (stated plainly)

1. **Single-operator key.** One RSA key signs mandates and auths. No threshold
   signing, no HSM, no key-rotation ceremony yet. Key compromise breaks
   *future* signature trust (revocation lists + anchored history still expose it).
2. **Store is a single database.** Postgres/SQLite availability is a liveness
   dependency; degraded-mode boot keeps the API alive read-only.
3. **Clock skew.** Expiry checks tolerate ±30s of clock drift; no distributed
   timestamping.
4. **Anchors are as strong as their destination.** A JSONL file on the same disk
   is weaker than a git push to GitHub. Publish roots outside the operator's
   blast radius for real independence.
5. **Prompt-layer attacks.** AION constrains what an agent *can do*, not what it
   *wants to do*. A prompt-injected agent inside its mandate can still cause
   in-boundary damage — caps, allowlists and approvals reduce blast radius,
   they do not eliminate intent.

## 5. Verification recipe (for auditors / counterparties)

```bash
pip install aion-core==<pinned>
aion pay-verify <jti>                       # signature + binding checks
aion pay-chain <mandate_id>                 # recompute chain integrity
aion anchor-verify <mandate_id>             # compare against published root
aion dispute <mandate_id> --save            # export bundle (incl. bundle_hash)
```

A third party only needs: the exported bundle, the published anchor file,
and the public key. No access to the operator's database is required for
signature/binding/chain checks; anchoring extends this to *liveness* of the history.

## 6. Roadmap (ordered by trust value)

- [x] External anchoring of payment-chain roots (this release)
- [ ] Anchor the full receipt/audit chain, not only payments
- [ ] RFC-3161 / OpenTimestamps trusted timestamps on anchors
- [ ] Key rotation + revocation registry (signed, replicated)
- [ ] Cloud verification API as an independent root (operator = AION, not the agent's owner)
- [ ] Third-party security audit before enterprise claims
