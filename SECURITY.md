# Security Policy

AION is a trust layer: it is about authority, proofs, and limits for AI agents.
That makes its own security posture part of the product, so this file states
exactly how secrets and keys are handled.

## Reporting a vulnerability

Open a private report via GitHub Security Advisories
(https://github.com/Sourabh1845/aion-protocol/security/advisories/new) or email
the maintainer. Please include: affected version, a minimal reproduction, and
what you expected vs what happened. We aim to acknowledge within 72 hours.

Please do not open a public issue for an unpatched vulnerability.

## Credential handling rules (enforced in code and in CI)

1. **No secrets in source.** API keys, DB URLs, and signing keys come from the
   environment only. There is a test-labelled rule: if you find a hardcoded
   credential, it is a bug - report it.
2. **Fail closed.** The hosted API requires `AION_API_KEY`. If it is unset the
   server returns `503` instead of falling back to any well-known default
   (see `aion/auth_middleware.py`).
3. **The local dev key is opt-in.** `aion-dev-key-local` is public knowledge
   (it is in this repo), so it is only accepted when a developer starts the
   server with `AION_ALLOW_DEV_KEY=1`. It is never used as an implicit fallback.
4. **Signing keys never live in the package.** Mandate/token signing keys are
   read from `/etc/secrets` (hosted) or `~/.aion/keys` (default), overridable with
   `AION_HOME` / `AION_KEY_DIR`. Keys written by <= 2.3.2 next to the installed
   package are migrated on first use, because a reinstall would otherwise destroy
   a user's signing identity. Receipts and dispute bundles contain public keys and
   hashes, never private material.
5. **Receipts redact secrets.** Metadata is passed through a redactor before
   hashing (only a hash of a redacted value is ever stored).
6. **Rotate on exposure.** If a key is ever committed, rotate it at the source
   (Render/Vercel/PyPI/etc.) - removing the commit is not enough, because git
   history keeps the old value.

## Rotation runbook

1. Generate a new key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Set it as `AION_API_KEY` in the hosting environment (e.g. Render -> Environment).
3. Update callers (`.env`, CI secrets, local shells) and redeploy.
4. Confirm the old key is rejected: it must return `401 Invalid or missing API key`.

## Scope

In scope: `aion-core` on PyPI, this repository, and the hosted verification API.
Out of scope: third-party rails (x402 facilitators, chains, model providers) and
anything requiring credentials we do not own.

## Honest limits

Tamper-evidence is only as strong as the operator running it: a local chain can
be rewritten by whoever holds the store. That is exactly why external anchoring
exists (`aion anchor`), and why `THREAT_MODEL.md` lists what is cryptographically
verifiable versus operator-held. We would rather state that plainly than overclaim.
