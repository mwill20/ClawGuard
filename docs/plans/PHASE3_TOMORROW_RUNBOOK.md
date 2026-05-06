# Phase 3 Tomorrow Runbook - May 6, 2026

Status: Active runbook; partial completion as of 2026-05-06 13:10 UTC
Purpose: Confirm daily schedule health before starting Phase 3 runtime-event instrumentation.

## Current State Snapshot

As of 2026-05-06 13:10 UTC:

- The 2026-05-06 manual compile-only run at 05:13 UTC sent the digest email and wrote schema `1.2` telemetry. Manual gate satisfied.
- The scheduled 16:30 UTC compile has not yet run. Schedule gate pending.
- Cron-confirm for 2026-05-06 currently shows the 05:13 manual compile entry only; re-run after 16:35 UTC for the scheduled-compile evidence the runbook requires.

## Context

On May 5, 2026, the daily cron schedule ran, but the digest email did not send because the host-side `staggered_cron.sh` wrapper did not pass `CLAWGUARD_EMAIL_TO` into the compile container. The wrapper was fixed and deployed, and a compile-only verification at `2026-05-06 05:13 UTC` sent the digest email successfully.

The remaining target is the real scheduled May 6 run:

| Time PT | Time UTC | Job |
|---|---:|---|
| 9:00 AM | 16:00 | LinkedIn maintenance search |
| 9:10 AM | 16:10 | CyberSecJobs maintenance search |
| 9:20 AM | 16:20 | USAJobs native API search |
| 9:30 AM | 16:30 | Compile digest, email, post-compile telemetry |

## Success Criteria

Run after 9:35 AM PT / 16:35 UTC on May 6, 2026.

Required:

- `compile_2026-05-06.log` exists from the scheduled compile.
- Compile log includes `Email digest sent to`.
- `telemetry_latest.json` validates as schema `1.2`.
- `telemetry_latest.md` is timestamped after the scheduled compile.
- If at least one real job was evaluated, detector activation lines appear as expected.

Conditional:

- If `0 jobs to evaluate`, detector activation lines are not expected. Do not mark ASI02 activation confirmed.
- If no finding-bearing real session exists, do not export one.
- Do not seed live providers with synthetic malicious jobs.

## Commands

PowerShell from repo root:

```powershell
Set-Location C:\Projects\ClawGuard
.\scripts\check_cron_confirmation.ps1 -Date 2026-05-06
.\scripts\check_latest_telemetry.ps1
```

Optional log check:

```powershell
ssh -o BatchMode=yes root@31.97.139.139 "grep -n 'Email digest sent\|Email not configured\|ClawGuard ASI02 detector module active\|jobs to evaluate' /docker/openclaw-utxu/data/clawguard/logs/compile_2026-05-06.log /docker/openclaw-utxu/data/clawguard/logs/cron_stdout.log | tail -80"
```

## Decision Table

| Observation | Action |
|---|---|
| Email sent, telemetry validates, 0 jobs evaluated | Mark schedule/email healthy; leave ASI02 activation as future evidence trigger |
| Email sent, telemetry validates, jobs evaluated, ASI02 activation logged | Mark ASI02 activation confirmed in local checklist |
| Email sent, telemetry validates, jobs evaluated, ASI02 activation missing | Inspect deploy/runtime drift; redeploy only after finding cause |
| Email not configured or not sent | Check `.env` for `CLAWGUARD_EMAIL_FROM`, `CLAWGUARD_EMAIL_PASSWORD`, `CLAWGUARD_EMAIL_TO`; verify host wrapper contains `CLAWGUARD_EMAIL_TO` forwarding |
| No scheduled compile log | Check host crontab, cron service status, and `cron_stdout.log` |
| Finding-bearing telemetry exists | Pull through manual curated export, redact, validate, then decide whether to commit |

## Phase 3 Go/No-Go

Go for Phase 3 runtime-event implementation when:

- The daily schedule is running.
- Email delivery is confirmed after scheduled compile.
- Telemetry schema `1.2` is confirmed from the deployed hook.
- No deploy drift exists for runtime, detections, post-compile hook, or cron wrapper.

No-go until fixed:

- Missing scheduled compile.
- Email delivery fails.
- Telemetry schema falls back to legacy `1.0`.
- Runtime/check scripts require manual secret exposure to diagnose.
