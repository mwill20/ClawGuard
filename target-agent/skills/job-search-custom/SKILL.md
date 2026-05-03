---
name: job-search-custom
description: "Persistent job-search pipeline with SQLite deduplication, low-volume maintenance search, resume scoring, application material prep, ASI06 job-content checks, and ClawGuard telemetry."
metadata:
  openclaw:
    requires:
      bins:
        - python3
    optionalEnv:
      - OXYLABS_AISTUDIO_API_KEY
      - BRAVE_SEARCH_API_KEY
      - USAJOBS_AUTH_KEY
      - USAJOBS_USER_AGENT
---

# Job Search Custom Skill

Persistent, low-volume job-search pipeline used as the primary OpenClaw telemetry source for ClawGuard Phase 1.

The skill searches selected job sources, deduplicates results in SQLite, scores jobs against local profile data, prepares application materials on demand, and records ASI06 job-content findings. Human approval is required for any submission.

## Current Maintenance Mode

```text
Daily 9:00 AM PT  LinkedIn      -> DB insert and dedup
Daily 9:10 AM PT  CyberSecJobs  -> DB insert and dedup
Daily 9:20 AM PT  USAJobs API   -> DB insert and dedup
Daily 9:30 AM PT  Compile digest, no auto-prepare, no JD enrichment
                 -> ClawGuard post-compile telemetry summary
```

Maintenance mode intentionally keeps volume low because the user is already in active interview and offer loops.

## Provider Posture

- Brave Search is the current free-tier fallback for normal job-board discovery.
- USAJobs uses the native USAJobs API when `USAJOBS_AUTH_KEY` and `USAJOBS_USER_AGENT` are configured.
- Oxylabs remains supported in code but is disabled in the active maintenance schedule with `CLAWGUARD_DISABLE_OXYLABS=1`.
- The prior Oxylabs `400 Bad Request` issue is not blocking the active maintenance path.

## Commands

Initialize database:

```bash
python3 job_search_secure.py init-db
```

Search jobs:

```bash
# Single site
python3 job_search_secure.py search --query "SOC Analyst" --location "Seattle, WA" --sites linkedin

# All configured sites with a budget cap
python3 job_search_secure.py search --query "Security Engineer" --location "Seattle, WA" --sites all --budget 30

# Force Brave or USAJobs provider during verification
python3 job_search_secure.py search --query "SOC Analyst" --location "Remote" --sites linkedin --provider brave
python3 job_search_secure.py search --query "Security Analyst" --location "Seattle, WA" --sites usajobs --provider usajobs
```

Run digest:

```bash
# Single-site maintenance run, normally called by cron
python3 job_search_secure.py digest --site linkedin --budget 2 --max-results-per-site 5 --no-notify

# Compile current-day results without preparing applications
python3 job_search_secure.py digest --compile --format telegram --no-prepare

# Manual validation compile with JSON output and no notification
python3 job_search_secure.py digest --compile --no-prepare --no-notify --format json
```

Score and browse:

```bash
python3 job_search_secure.py score --status found --min-score 0.40
python3 job_search_secure.py browse --summary
python3 job_search_secure.py browse --since 24h
python3 job_search_secure.py browse --job-id abc123
```

Prepare, track, and submit:

```bash
python3 job_search_secure.py prepare --job-id abc123def456
python3 job_search_secure.py track --job-id abc123def456 --status applied
python3 job_search_secure.py submit --job-id abc123def456 --confirmation-code A1B2C3D4
```

Utility:

```bash
python3 job_search_secure.py quota
python3 job_search_secure.py sites
python3 job_search_secure.py export --status scored --output scored.json
python3 job_search_secure.py migrate --source /path/to/old/digests/
```

## Supported Sites

| Site | Key | Active Maintenance | Primary Maintenance Provider |
|---|---|---:|---|
| LinkedIn | `linkedin` | Yes | Brave |
| CyberSecJobs | `cybersecjobs` | Yes | Brave |
| USAJobs | `usajobs` | Yes | Native USAJobs API |
| Indeed | `indeed` | No | Oxylabs when re-enabled |
| Monster | `monster` | No | Oxylabs when re-enabled |
| Dice | `dice` | No | Oxylabs when re-enabled |
| InfoSec Jobs | `infosecjobs` | No | Oxylabs or Brave when re-enabled |
| SimplyHired | `simplyhired` | No | Oxylabs when re-enabled |
| RemoteHunter | `remotehunter` | No | Oxylabs when re-enabled |

## Persistent Data

All persistent runtime data is under `/data/clawguard/` inside the container-backed volume:

```text
/data/clawguard/
  jobs.db
  tailoring_rules.json
  applications/{job_id}/
  digests/
  telemetry/
  logs/
```

## Environment

Provider and runtime controls:

```text
CLAWGUARD_DATA_DIR=/data/clawguard
BRAVE_SEARCH_API_KEY=<secret>
USAJOBS_AUTH_KEY=<secret>
USAJOBS_USER_AGENT=<registered email>
OXYLABS_AISTUDIO_API_KEY=<secret>
CLAWGUARD_SEARCH_PROVIDER=auto
CLAWGUARD_DISABLE_OXYLABS=1
CLAWGUARD_FALLBACK_ON_EMPTY=0
CLAWGUARD_HTTP_TIMEOUT_SECONDS=20
```

Maintenance volume controls:

```text
CLAWGUARD_AUTO_PREPARE_THRESHOLD=0.75
CLAWGUARD_ENRICHMENT_DAILY_CAP=0
CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE=5
CLAWGUARD_DIGEST_TOP_MATCH_LIMIT=10
```

ASI06 tuning:

```text
CLAWGUARD_SKILL_STUFFING_THRESHOLD=15
CLAWGUARD_SKILL_STUFFING_PENALTY=0.15
```

## ASI06 Runtime Checks

Inline rules currently record findings to `job_security_findings`:

- `ASI06_SKILL_STUFFING`
- `ASI06_PROMPT_INJECTION`
- `ASI06_PII_REQUEST`
- `ASI06_URL_MISMATCH`

Findings preserve:

- `job_id`
- `agent_session_id`
- `rule_id`
- `severity`
- `message`
- `evidence`
- `context`
- `detected_at`

Prompt-injection evidence includes `pattern`, `matched_text`, and `snippet`.

The standalone ClawGuard detector module lives at:

```text
detections/asi06_jd_content/detector.py
```

The OpenClaw runtime remains inline until the next deploy-safe integration pass.

## Application Prep Rules

Materials are generated using local resume/profile data only:

- No fabrication.
- No embellishment.
- Resume and contact data are never sent to job boards by this skill.
- Generated materials include human review markers.
- Confirmation code is required before a submission can be marked approved.

## Security Guarantees

- No auto-submit capability for job boards.
- Resume data stays local.
- Provider calls are logged.
- Application prep is disabled in the active cron path.
- JD enrichment is disabled in the active cron path.
- ASI06 checks run before generated materials are trusted.
- Post-compile telemetry gives ClawGuard a session-correlated summary after successful digest compilation.

## When To Use

Use this skill when the user asks to:

- Search for jobs or find openings.
- Score or rank jobs against the local profile.
- Prepare cover letters or application materials.
- Run or inspect the daily digest.
- Browse the job database.
- Track application status.
- Check provider quota or source health.

Always prefer this skill over generic web search for job-related queries in the OpenClaw target.
