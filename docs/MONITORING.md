# Monitoring and Maintenance

## Monitoring Plan

| Area | What to Monitor | Why It Matters |
|---|---|---|
| Cron execution | Search and compile logs | Detect missed runs |
| Detector mode | `ClawGuard ASI06 detector module active` log line | Confirms detector-backed path |
| Finding counts | `telemetry_latest.json` and `job_security_findings` | Detect suspicious content or noise |
| Provider results | Per-source job counts | Detect provider failure or duplicates |
| Credits | `credits_used_today`, `credits_remaining` | Avoid unexpected provider cost |
| Telemetry writes | `telemetry_latest.md` timestamp | Confirm post-compile hook runs |

## Logs Produced

Runtime and host logs include:

```text
job_search.log
job_search_audit.log
/docker/openclaw-utxu/data/clawguard/logs/cron.log
/docker/openclaw-utxu/data/clawguard/logs/search_<site>_<date>.log
/docker/openclaw-utxu/data/clawguard/logs/compile_<date>.log
/docker/openclaw-utxu/data/clawguard/logs/post_compile_<date>.log
```

Telemetry artifacts:

```text
/data/clawguard/telemetry/telemetry_latest.json
/data/clawguard/telemetry/telemetry_latest.md
```

## Local Helper Commands

Inspect latest telemetry:

```powershell
.\scripts\check_latest_telemetry.ps1
```

Confirm the daily cron used the detector-backed ASI06 path, with ASI01/ASI02 activation notes until those detectors first log:

```powershell
.\scripts\check_cron_confirmation.ps1
```

Dry-run a curated telemetry export:

```powershell
.\scripts\export_telemetry.ps1 -DryRun -Sessions digest-20260503T163003-b91b67e1
```

Validate the first curated Phase 2 clean-baseline export:

```powershell
python -B scripts\validate_telemetry.py --input lessons\telemetry\2026-05\digest-20260505T163003-d9133ff9\telemetry.json
```

Deploy the OpenClaw runtime package after code changes:

```powershell
.\scripts\deploy_openclaw_skill.ps1
```

Run the full local preflight before committing:

```powershell
.\scripts\preflight.ps1
```

## Maintenance Schedule

Current daily schedule:

| Time PT | Job |
|---|---|
| 9:00 AM | LinkedIn maintenance search |
| 9:10 AM | CyberSecJobs maintenance search |
| 9:20 AM | USAJobs native API search |
| 9:30 AM | Compile digest and post-compile telemetry hook |

## Health Checks

Manual checks:

```powershell
.\scripts\preflight.ps1
.\scripts\check_latest_telemetry.ps1
```

VPS checks:

```bash
cat /data/clawguard/telemetry/telemetry_latest.md
sqlite3 /data/clawguard/jobs.db "SELECT rule_id, COUNT(*) FROM job_security_findings GROUP BY rule_id;"
```

## Drift Monitoring

Not implemented.

Recommended future checks:

- Provider result count drift.
- Finding count drift by source platform.
- False-positive review log.
- Rule version drift between repo and deployed container.
