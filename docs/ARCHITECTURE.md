# Architecture

## System Overview

ClawGuard monitors a real OpenClaw `job-search-custom` deployment and turns job-search activity into security telemetry.

The current Phase 1 architecture focuses on ASI06 job-description content detection:

```text
Job sources
  -> OpenClaw job_search_secure.py
  -> SQLite jobs.db
  -> ASI06 detector module
  -> job_security_findings
  -> daily digest JSON
  -> post-compile telemetry JSON/Markdown
  -> curated lessons and baselines
```

## Component Diagram

```text
LinkedIn / CyberSecJobs / USAJobs
             |
             v
target-agent/skills/job-search-custom/job_search_secure.py
             |
             +--> SQLite jobs, search_runs, quota
             |
             +--> detections/asi06_jd_content/detector.py
                         |
                         v
                 job_security_findings
                         |
                         v
target-agent/skills/job-search-custom/clawguard_post_compile.sh
             |
             v
/data/clawguard/telemetry/telemetry_latest.json
/data/clawguard/telemetry/telemetry_latest.md
```

## Data Flow

1. Cron runs `staggered_cron.sh` for one source at a time.
2. `job_search_secure.py` searches configured providers and stores jobs in SQLite.
3. During scoring/compile, `run_jd_security_detections()` evaluates job content.
4. The runtime calls `detections/asi06_jd_content/detector.py`.
5. Findings are stored in `job_security_findings`.
6. Compile creates a digest with `agent_session_id`.
7. `clawguard_post_compile.sh` queries findings for that session and writes telemetry artifacts.

## Trust Boundaries

| Boundary | Untrusted Side | Trusted/Controlled Side | Control |
|---|---|---|---|
| Job source ingestion | Job postings and search snippets | OpenClaw runtime | Treat external content as data |
| Detector boundary | Job text and apply URLs | ASI06 detector rules | Evidence-preserving findings |
| Persistence boundary | Runtime events | SQLite database | `job_id`, `agent_session_id`, JSON evidence/context |
| Deployment boundary | Manual file copy | Running OpenClaw container | Syntax/import checks before verification |
| Telemetry boundary | Continuous VPS state | Curated repo artifacts | Manual export only |

## Design Decisions

| Decision | Chosen Approach | Alternatives Considered | Rationale | Trade-off |
|---|---|---|---|---|
| ASI06 integration | Detector module required | Inline fallback | Removes duplicate detection logic after VPS cron confirmation | Requires packaged deployment discipline |
| Telemetry storage | SQLite plus JSON/Markdown summaries | SIEM integration or cloud database | Simple, inspectable, enough for Phase 1 | Limited query/scale features |
| Daily schedule | Staggered low-volume cron | High-volume all-source crawl | Reduces noise and cost during active interview cycle | Slower data accumulation |
| Provider posture | Brave and USAJobs zero-credit path; Oxylabs disabled | Oxylabs full-volume search | Avoids credit use and rate risk | Less source coverage |
| ASI01 status | Scaffold only | Build speculative detector immediately | Avoids regex-first design for semantic threat | No runtime ASI01 findings yet |

## Implemented Guardrails

- ASI06 content checks for prompt injection, PII requests, skill stuffing, and URL mismatch.
- `agent_session_id` correlation.
- Cron disables application auto-prep.
- `.env.example` placeholders; `.env` ignored.
- Post-compile telemetry only after successful digest compile.

## Recommended (not implemented here)

- Schema validation for telemetry JSON.
- Prompt sanitization or quarantine before future LLM summarization.
- Semantic guardrails for ASI01 using deterministic policy checks or LLM-as-judge.
- Signed deployment bundle for the OpenClaw script and `detections/` package.
- CI/CD packaging for VPS deployment.
