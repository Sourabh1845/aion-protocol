# AION distribution playbook

Status: release **v2.3.2** is live on PyPI (`aion-core`) and on `main`.

| Asset | File | Channel | Status |
|---|---|---|---|
| Show HN post | `01-show-hn.md` | news.ycombinator.com | ready to post |
| X/Twitter thread | `02-x-thread.md` | X | ready to post |
| x402 community post | `03-x402-community-post.md` | x402 GitHub Discussions / Discord | ready to post |
| Rogue-agent demo script | `04-rogue-agent-demo.md` | screen recording (Loom/YouTube) -> HN + X | script ready, recording pending |
| Reapplication answers | `05-reapply-answers.md` | EverVent / Z-Fellows forms | template with TODOs |

## Order of operations (do not reorder)

1. **Rotate the hosted API key first.** `aion-prod-key-2026` was committed in
   earlier commits (removed in v2.3.2, but git history keeps it). Set a new
   `AION_API_KEY` on the host and redeploy. Anyone reading the repo with the old
   key could burn the rate limit on a free Render instance.
2. **Warm the demo.** Hit https://aion-protocol.onrender.com/health so the free
   instance is not cold-starting when traffic arrives (cold start is 30-60s).
3. **Post the rogue-agent recording** (or a terminal GIF of `aion demo`) as the
   visual anchor - HN/X threads do far better with a 30-60s clip than with text.
4. **Show HN** (US weekday morning, ~14:00-16:00 UTC performs best), then reply
   to every comment for the first 3 hours. Link the recording, not the landing page.
5. **X thread** the same day, quoting the HN discussion.
6. **x402 community** post the day after, when the HN traffic has settled - that
   audience is technical and will read the code.
7. **Reapplications** last, after you can cite real numbers (stars, installs,
   threads, inbound).

## Hard rules for all copy

- Never claim more than the code proves. Say "tamper-evident unless you publish
  the root somewhere you do not control" - that is the honest version.
- AION does **not** move money. Rails like x402 do. AION decides whether a
  payment is allowed and proves what happened.
- One maintainer, no funding, no security audit. State it before someone digs.
- Every claim must be reproducible with `pip install aion-core` and `aion demo`.

## Links to reuse

- PyPI: https://pypi.org/project/aion-core/
- GitHub: https://github.com/Sourabh1845/aion-protocol
- Landing: https://sourabh1845.github.io/aion-protocol
- Live API: https://aion-protocol.onrender.com
- Threat model: https://github.com/Sourabh1845/aion-protocol/blob/main/THREAT_MODEL.md
- Security policy: https://github.com/Sourabh1845/aion-protocol/blob/main/SECURITY.md
