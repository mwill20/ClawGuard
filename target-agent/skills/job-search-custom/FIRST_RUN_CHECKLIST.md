# Maintenance Run Observation Checklist

Last updated: 2026-05-03

This checklist replaces the original March full-volume first-run checklist. The active pipeline is now a low-volume ClawGuard telemetry generator.

## Expected Daily Schedule

| Time PT | Command |
|---|---|
| 9:00 AM | `staggered_cron.sh linkedin` |
| 9:10 AM | `staggered_cron.sh cybersecjobs` |
| 9:20 AM | `staggered_cron.sh usajobs` |
| 9:30 AM | `staggered_cron.sh compile` |

## Quick Health Check

Run on the VPS:

```bash
ssh root@31.97.139.139

tail -80 /docker/openclaw-utxu/data/clawguard/logs/cron.log
tail -80 /docker/openclaw-utxu/data/clawguard/logs/compile_$(date +%Y-%m-%d).log
tail -80 /docker/openclaw-utxu/data/clawguard/logs/post_compile_$(date +%Y-%m-%d).log
```

Check latest telemetry:

```bash
cat /docker/openclaw-utxu/data/clawguard/telemetry/telemetry_latest.md
```

Check database summary:

```bash
docker exec \
  -e CLAWGUARD_DATA_DIR=/data/clawguard \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 -B job_search_secure.py browse --summary
```

## Findings Query

```bash
docker exec -i openclaw-utxu-openclaw-1 sqlite3 /data/clawguard/jobs.db <<'SQL'
SELECT
  agent_session_id,
  rule_id,
  severity,
  json_extract(context, '$.source_platform') AS source_platform,
  json_extract(context, '$.source_field') AS source_field,
  detected_at
FROM job_security_findings
ORDER BY detected_at DESC
LIMIT 20;
SQL
```

## Expected Signals

| Signal | Expected | Investigate If |
|---|---|---|
| Cron chain | Four jobs complete daily | Any site or compile step missing |
| Credits used | 0 in maintenance mode | Oxylabs was called unexpectedly |
| Auto-prepared | 0 | Compile omitted `--no-prepare` |
| JD enrichment | 0 | `CLAWGUARD_ENRICHMENT_DAILY_CAP` not applied |
| Findings | 0 is acceptable | Any finding needs triage and evidence review |
| `telemetry_latest.*` | Updated after compile | Post-compile hook failed or was not executable |

## Manual Provider Checks

Force Brave:

```bash
docker exec \
  -e BRAVE_SEARCH_API_KEY="$(grep '^BRAVE_SEARCH_API_KEY=' /docker/openclaw-utxu/.env | cut -d= -f2-)" \
  -e CLAWGUARD_DATA_DIR=/data/clawguard \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 -B job_search_secure.py search \
    --query "SOC Analyst" --location "Remote" --sites linkedin --provider brave --max-results 5
```

Force USAJobs:

```bash
docker exec \
  -e USAJOBS_AUTH_KEY="$(grep '^USAJOBS_AUTH_KEY=' /docker/openclaw-utxu/.env | cut -d= -f2-)" \
  -e USAJOBS_USER_AGENT="$(grep '^USAJOBS_USER_AGENT=' /docker/openclaw-utxu/.env | cut -d= -f2-)" \
  -e CLAWGUARD_DATA_DIR=/data/clawguard \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 -B job_search_secure.py search \
    --query "Security Analyst" --location "Seattle, WA" --sites usajobs --provider usajobs --max-results 5
```

## Baseline Data To Record

```text
Date:
Agent session:
LinkedIn new jobs:
CyberSecJobs new jobs:
USAJobs new jobs:
Total jobs in digest:
Strong matches:
Good matches:
Moderate matches:
Auto-prepared:
Credits used:
ASI06 findings:
Telemetry file:
Anomalies:
```

After a clean run, no action is needed beyond letting sessions accumulate. After a finding, preserve `telemetry_latest.json`, review `pattern`, `matched_text`, and `snippet`, then decide whether the rule should stay inline or be extracted.
