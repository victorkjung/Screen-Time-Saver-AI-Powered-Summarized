# ⚠️ DEPRECATED — this pipeline is not in use

`screen-time-saver` was the original fetch → transcribe → summarize → Telegram
digest pipeline. It is **no longer part of the live Lila system** and its VPS
cron was removed on 2026-07-15 (it had been failing every weekday on a dead
OpenAI key). Kept for history only.

## Where its role went

The SPEC (`podcast-news-summarizer-voice`) assumed this pipeline would be
reused. It was not — the work was rebuilt elsewhere:

| Old role (here) | Now lives in |
|---|---|
| Fetch sources → transcribe → summarize → write digest | **`aura-talk-vault`** (Lovable app, `runDailyDigest()`), served at `GET /api/public/digest`. GitHub: `victorkjung/aura-talk-vault`. |
| Transcription backend | **`transcribe.vgh-usa.com`** (our transcribe-anything service on the VPS) |
| Read the digest to Victor over the phone | **`../lila-voice/`** — GitHub `victorkjung/lila-voice`, deployed VPS `/opt/lila-voice` |

Do **not** wire anything new to this repo. See
`vgh-shared-ops/runbooks/voice-agent-telephony-runbook.md` and the 2026-07-15
Lila session recap for the current architecture.
