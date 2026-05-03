# ClawGuard Telemetry Baseline 002

Date: YYYY-MM-DD
Target: OpenClaw job-search-custom autonomous maintenance pipeline
Environment: VPS `31.97.139.139`, container `openclaw-utxu-openclaw-1`

## Purpose

Capture the first fully autonomous daily cron-chain telemetry sample after the post-compile hook was deployed.

This baseline should prove that the 9:00-9:30 AM PT chain ran end to end without manual hook invocation.

## Cron Chain Proof

Expected schedule:

| Time PT | Job | Observed |
|---|---|---|
| 9:00 AM | LinkedIn maintenance search | TODO |
| 9:10 AM | CyberSecJobs maintenance search | TODO |
| 9:20 AM | USAJobs native API search | TODO |
| 9:30 AM | Compile digest and post-compile telemetry hook | TODO |

Evidence commands:

```bash
tail -80 /docker/openclaw-utxu/data/clawguard/logs/cron.log
cat /docker/openclaw-utxu/data/clawguard/telemetry/telemetry_latest.md
```

Local helper:

```powershell
.\scripts\check_latest_telemetry.ps1
```

## Digest Summary

```json
{
  "agent_session_id": "TODO",
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

| Source | New Jobs | Top Matches | Notes |
|---|---:|---:|---|
| LinkedIn | TODO | TODO | TODO |
| CyberSecJobs | TODO | TODO | TODO |
| USAJobs | TODO | TODO | TODO |

## ClawGuard Findings

Findings query:

```sql
SELECT
  agent_session_id,
  rule_id,
  severity,
  json_extract(context, '$.source_platform') AS source_platform,
  json_extract(context, '$.source_field') AS source_field,
  json_extract(context, '$.job_title') AS job_title,
  detected_at
FROM job_security_findings
ORDER BY detected_at DESC
LIMIT 20;
```

Observed findings:

- TODO

If there are 0 findings, record that as a clean-content telemetry signal rather than a failure.

## Comparison To Baseline 001

Baseline 001:

- Session: `digest-20260502T143953-c9eb7f4c`
- Jobs evaluated: 22
- ASI06 findings: 0
- Credits used: 0
- Auto-prepared: 0

Baseline 002 comparison:

- Session: TODO
- Jobs evaluated: TODO
- ASI06 findings: TODO
- Credits used: TODO
- Auto-prepared: TODO

## Decision

Choose one after reviewing the autonomous run:

- If ASI06 findings exist: triage evidence and prepare for ASI06 extraction.
- If this is the third clean session: start or update the ASI01 scaffold.
- If cron or telemetry failed: fix the chain before adding new detection work.
