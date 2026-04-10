# AION Protocol — Control What AI Agents Can Do

AION is a cryptographic authority governance layer for AI agents. Every agent action requires a signed, scoped, one-time token — before anything happens.

**Live API:** https://aion-protocol.onrender.com  
**Landing Page:** https://sourabh1845.github.io/aion-protocol  
**PyPI:** https://pypi.org/project/aion-protocol/

---

## The Problem

AI agents act without authorization. They can:
- Execute the same action twice (replay attack)
- Exceed their permitted scope
- Act without any audit trail

AION fixes this.

---

## How It Works

1. Agent requests a signed token from AION for a specific scope
2. AION issues a time-limited, RSA-signed, one-time token
3. Agent presents token before acting — AION verifies and allows or blocks
4. Token is consumed — replay attempts are permanently blocked

---

## Quickstart

```bash
pip install aion-protocol
```

**Issue a token:**
```bash
curl -X POST https://aion-protocol.onrender.com/issue \
  -H "X-AION-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"scope": "delete.file", "issuer": "my-agent"}'
```

**Enforce:**
```bash
curl -X POST https://aion-protocol.onrender.com/enforce \
  -H "X-AION-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"jti": "token-id-here", "scope": "delete.file"}'
```

---

## What AION Blocks

| Attack | Result |
|--------|--------|
| Fake token | `NOT_FOUND` |
| Replay attack | `CONSUMED` |
| Scope escalation | `SCOPE_MISMATCH` |
| Invalid API key | `401 UNAUTHORIZED` |

---

## Stack

- FastAPI + PostgreSQL + Redis (Upstash)
- RSA 2048-bit token signing
- Docker + Render cloud deployment
- LangChain + CrewAI adapters included

---

## Links

- [API Documentation](https://aion-protocol.onrender.com/docs)
- [Landing Page](https://sourabh1845.github.io/aion-protocol)
- [PyPI Package](https://pypi.org/project/aion-protocol/)

---

Built by Sourabh Ranjan Sahoo