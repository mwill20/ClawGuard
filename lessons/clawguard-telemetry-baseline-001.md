# ClawGuard Telemetry Baseline 001

Date: 2026-05-02
Target: OpenClaw job-search-custom maintenance pipeline
Environment: VPS `31.97.139.139`, container `openclaw-utxu-openclaw-1`

## Purpose

This baseline captures the first useful OpenClaw telemetry sample after the job-search pipeline was reduced from an application-oriented workflow to a low-volume ClawGuard telemetry generator.

The run verifies that OpenClaw can produce real operational events without spending Oxylabs credits, auto-preparing applications, or enriching job descriptions.

## Maintenance Posture

- Oxylabs disabled: `CLAWGUARD_DISABLE_OXYLABS=1`
- JD enrichment disabled: `CLAWGUARD_ENRICHMENT_DAILY_CAP=0`
- Application auto-prep disabled in cron: `--no-prepare`
- Notifications disabled during manual validation: `--no-notify`
- Result cap: `CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE=5`
- Digest display cap: `CLAWGUARD_DIGEST_TOP_MATCH_LIMIT=10`

## Manual Runs

### LinkedIn

Command path: `staggered_cron.sh linkedin`

Observed behavior:

- Oxylabs initially returned `400 Bad Request`.
- Brave fallback succeeded.
- 14 new LinkedIn-shaped jobs inserted into SQLite.
- Cost: 0 credits.

Telemetry value:

- Provider failure event: Oxylabs HTTP 400.
- Fallback success event: Brave search completed.
- DB insert and dedup counters.
- Search provenance by provider and source.

### CyberSecJobs

Command path: `staggered_cron.sh cybersecjobs`

Observed behavior:

- Provider list: Brave only.
- Query group 1 returned 5 results, 5 new.
- Query group 2 returned 5 results, 2 new.
- Query group 3 returned 1 result, 1 new.
- Total new jobs: 8.
- Cost: 0 credits.

Telemetry value:

- Successful low-cost source collection.
- Dedup behavior across related query groups.
- Cybersecurity-specific source coverage.

### USAJobs

Command path: `staggered_cron.sh usajobs`

Observed behavior:

- Provider list: USAJobs native API, Brave fallback available.
- USAJobs API authenticated successfully.
- All three query groups returned 0 results for Seattle, WA.
- Cost: 0 credits.

Telemetry value:

- Native API auth path verified.
- Zero-result source behavior captured.
- No fallback needed because the native provider completed successfully.

## Digest Compile

Command path:

```bash
job_search_secure.py digest --compile --no-prepare --no-notify --format json
```

Environment override:

```bash
CLAWGUARD_ENRICHMENT_DAILY_CAP=0
```

Summary:

```json
{
  "agent_session_id": "digest-20260502T143953-c9eb7f4c",
  "total_found": 22,
  "new_jobs": 22,
  "strong_matches": 4,
  "good_matches": 10,
  "moderate_matches": 5,
  "auto_prepared": 0,
  "credits_used_today": 0,
  "credits_remaining": 1000,
  "total_jobs_in_db": 177
}
```

Top signal examples:

- AWS DC SOC Security Analyst II: strong match, LinkedIn source.
- Cyber Threat Hunter Jobs: strong match, CyberSecJobs source.
- Cyber Threat Intelligence Analyst: good match, LinkedIn source.

## ClawGuard Detection Relevance

This baseline provides real events for Phase 1 ClawGuard integration:

- Provider failure and fallback telemetry.
- Search provider attribution.
- Job source attribution.
- DB insert and dedup outcomes.
- Scoring distribution.
- No-prep and no-enrichment control validation.
- Early ASI06 job content findings through `job_security_findings`.

## Follow-Up

- Keep ASI06 inline through additional real events.
- Add `agent_session_id` and structured `context` to `job_security_findings`.
- Extract ASI06 into a dedicated `detections/` module after enough live examples exist.
- Keep Oxylabs debug isolated from the maintenance pipeline.
