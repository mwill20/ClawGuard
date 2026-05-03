# Skill Test Log: job-search-custom

Last updated: 2026-05-03

## Current Validation Summary

The `job-search-custom` skill is working as the OpenClaw telemetry target for ClawGuard Phase 1.

Verified current behavior:

- Brave Search fallback works for LinkedIn-shaped maintenance searches.
- CyberSecJobs maintenance search works through Brave.
- USAJobs native API authentication works.
- Compile mode emits an `agent_session_id`.
- Compile mode can run with `--no-prepare`.
- JD enrichment can be disabled with `CLAWGUARD_ENRICHMENT_DAILY_CAP=0`.
- ASI06 findings table exists with correlation fields.
- Post-compile telemetry hook writes JSON and Markdown summaries.
- Manual telemetry export works from the local repo.

## 2026-05-02 Maintenance Validation

| Test | Result |
|---|---|
| LinkedIn maintenance run | Brave fallback inserted 14 new jobs, 0 credits |
| CyberSecJobs maintenance run | Brave inserted 8 new jobs, 0 credits |
| USAJobs native API run | Auth path verified, 0 matches, 0 credits |
| Digest compile | 22 jobs, 4 strong, 10 good, 5 moderate |
| Application prep | 0 auto-prepared packages |
| ASI06 findings query | 0 findings |
| Post-compile telemetry hook | Direct verification succeeded |

Baseline session:

```text
digest-20260502T143953-c9eb7f4c
```

Direct post-compile hook verification session:

```text
digest-20260502T163002-dbe409f3
```

## Current Expected Signals

| Signal | Expected |
|---|---|
| Credits used | 0 |
| Auto-prepared | 0 |
| JD enrichment | 0 in maintenance mode |
| ASI06 findings | 0 is valid unless a real unsafe posting appears |
| Telemetry output | `telemetry_latest.json` and `telemetry_latest.md` updated after compile |

## Historical March Validation

The first implementation used Oxylabs heavily and validated that:

- OpenClaw routed job-search requests to the custom skill.
- LinkedIn searches returned real structured job data.
- Rate limits and quota tracking were active.
- Resume data stayed local.
- Human approval gates prevented automatic submission.

That history remains useful, but it is not the active operating mode. The current maintenance path is Brave/USAJobs-first with Oxylabs disabled.

## Known Issues

| Issue | Status |
|---|---|
| Oxylabs `400 Bad Request` during later fallback testing | Deferred, not blocking |
| Full cron chain with post-compile hook | Scheduled to exercise automatically at 9:30 AM PT |
| First live ASI06 finding | Waiting on real telemetry |

## Sign-Off

Ready for current ClawGuard Phase 1 work: yes.
