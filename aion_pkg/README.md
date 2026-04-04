# AION Protocol

Immutable Authority Infrastructure for Autonomous AI Agents.

Before any AI agent can act in the world — it must be authorized.
AION issues, enforces, and immutably logs that authority.

---

## The Problem

AI agents are acting without permission systems.
They send emails, execute code, move data — with no cryptographic proof of who authorized them.
This is the core unsolved problem of the Autonomous AI Agent era.

---

## What AION Does

1. **Issue** — a signed authority token is created with scope + expiry
2. **Enforce** — agent must present token before acting
3. **Audit** — every action is immutably logged with hash chaining

No token = no action. Simple.

---

## Install

pip install aion-protocol

---

## Quickstart

Issue a token:
aion issue ops.read

Enforce it:
aion enforce <jti> ops.read

Revoke it:
aion revoke <jti>

---

## REST API

Start the server:
uvicorn aion.api:app --reload

Endpoints:
POST /issue
POST /enforce
GET  /verify/{jti}
POST /revoke/{jti}
GET  /health

API docs: http://127.0.0.1:8000/docs

---

## What AION Prevents

- Agents acting without permission
- Replay attacks — consumed tokens are blocked
- Scope escalation — ops.read cannot enforce ops.write
- Silent actions — every action is logged

---

## Built For

The Autonomous AI Agent era.
When millions of agents act in the world — authority infrastructure is not optional.

---

## Status

v2.0 — SQLite storage, REST API, 3 tests passing.

GitHub: https://github.com/Sourabh1845/aion-protocol