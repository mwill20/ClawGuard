# ClawGuard Telemetry Baseline 002

Date: 2026-05-03
Target: OpenClaw job-search-custom autonomous maintenance pipeline
Environment: VPS `31.97.139.139`, container `openclaw-utxu-openclaw-1`

## Purpose

This baseline captures the first fully autonomous daily cron-chain telemetry sample after the post-compile hook was deployed.

The run proves that the 9:00-9:30 AM PT chain executed end to end without manually invoking the hook.

## Cron Chain Proof

| Time PT | Job | Observed |
|---|---|---|
| 9:00 AM | LinkedIn maintenance search | Ran successfully |
| 9:10 AM | CyberSecJobs maintenance search | Ran successfully |
| 9:20 AM | USAJobs native API search | Ran successfully |
| 9:30 AM | Compile digest and post-compile telemetry hook | Ran successfully |

Session:

```text
digest-20260503T163003-b91b67e1
```

Telemetry output:

```text
/data/clawguard/telemetry/telemetry_2026-05-03_digest-20260503T163003-b91b67e1.json
/data/clawguard/telemetry/telemetry_2026-05-03_digest-20260503T163003-b91b67e1.md
/data/clawguard/telemetry/telemetry_latest.json
/data/clawguard/telemetry/telemetry_latest.md
```

## Digest Summary

```json
{
  "agent_session_id": "digest-20260503T163003-b91b67e1",
  "total_found": 0,
  "new_jobs": 0,
  "strong_matches": 0,
  "good_matches": 0,
  "moderate_matches": 0,
  "auto_prepared": 0,
  "credits_used_today": 0
}
```

## Source Breakdown

| Source | Provider Behavior | New Jobs | Notes |
|---|---|---:|---|
| LinkedIn | Brave returned 5 results for each query group | 0 | All returned jobs were already in SQLite |
| CyberSecJobs | Brave returned 5, 5, and 1 results | 0 | All returned jobs were already in SQLite |
| USAJobs | Native API authenticated and returned 0 results | 0 | No fallback needed because provider completed successfully |

## ClawGuard Findings

Observed findings:

- 0 ASI06 findings.
- 0 ASI01 findings; ASI01 is not implemented yet.

This is a clean-content telemetry signal, not a failed run.

## Important Interpretation

The digest line `Found 0 jobs, 0 new today` means there were 0 newly inserted jobs in the compile window.

It does not mean the source searches failed:

- LinkedIn returned candidates, but dedup marked them as already known.
- CyberSecJobs returned candidates, but dedup marked them as already known.
- USAJobs returned no native API matches.

The narrow future improvement is to report re-seen candidates separately from newly inserted jobs, for example:

```text
0 new, 26 re-seen
```

## Comparison To Baseline 001

| Metric | Baseline 001 | Baseline 002 |
|---|---:|---:|
| Jobs evaluated in compile | 22 | 0 |
| ASI06 findings | 0 | 0 |
| Credits used | 0 | 0 |
| Auto-prepared | 0 | 0 |
| Hook path | Manual validation | Autonomous cron chain |

## Decision

This run unlocks the ASI01 documentation scaffold because the project now has:

- A clean manual maintenance baseline.
- A clean post-compile hook validation.
- A clean autonomous cron-chain baseline.

Runtime ASI01 implementation should still wait for a live redirect signal or ASI06 prompt-injection finding.
