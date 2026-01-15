# AION v1 — Proof of Authority Governance

AION is a minimal, executable authority layer for AI agents.

Agents cannot act unless explicitly authorized.
Authority is verifiable, enforceable, single-use, and immutably logged.

This repository contains a working proof of Agent Sovereignty.

---

## What This Proves (Executable, Not Theoretical)

This system proves that:

- Authority can be ISSUED with a unique cryptographic identifier (JTI)
- Authority must be VERIFIED before execution
- Authority is ENFORCED at runtime
- Authority cannot be reused or escalated
- Every action is immutably logged with hash chaining

---

## Authority Lifecycle (Executed)

### 1. Issue Authority
Authority is issued with:
- scope (e.g. ops.read)
- expiry
- single-use constraint

(issued internally via CLI)

---

### 2. Enforce Authority (ALLOW)

Command:
python -m api.cli enforce <JTI> ops.read

Result:
{
  "status": "ENFORCED",
  "jti": "<JTI>",
  "scope": "ops.read"
}

---

### 3. Enforce Authority (DENY — Replay / Escalation)

Command:
python -m api.cli enforce <JTI> ops.write

Result:
{
  "error": "ENFORCEMENT_DENIED",
  "reason": {
    "error": "CONSUMED"
  }
}

This proves:
- Authority is single-use
- Scope escalation is blocked
- Replay attacks are prevented

---

## Immutable Audit Log

All actions are recorded in:

storage/audit_log.json

Each record contains:
- event type (GENESIS / ISSUE / VERIFY / ENFORCE)
- timestamp
- authority identifier (JTI)
- scope
- prev_hash for chain integrity

Any modification breaks the chain.

---

## What AION Prevents

- Agents acting without permission
- Reuse of consumed authority
- Scope escalation beyond issuance
- Unverifiable or silent agent actions

---

## Status

AION v1 authority lifecycle is complete, enforced, and reproducible.

This is a foundational governance layer for sovereign AI systems.
