# Architecture

## System Overview

ClawGuard monitors a real OpenClaw `job-search-custom` deployment and turns job-search activity into security telemetry.

The current architecture focuses on ASI06 job-description content detection, ASI01 goal-redirect classification, and ASI02 content-side tool-misuse detection:

```text
Job sources
  -> OpenClaw job_search_secure.py
  -> SQLite jobs.db
  -> ASI06 detector module
  -> ASI01 detector module
  -> ASI02 detector module
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
             +--> detections/asi01_goal_hijack/detector.py
             |
             +--> detections/asi02_tool_misuse/detector.py
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
5. The runtime passes ASI06 findings into `detections/asi01_goal_hijack/detector.py` as upstream corroboration.
6. The runtime passes ASI06 and ASI01 findings into `detections/asi02_tool_misuse/detector.py` as corroboration links.
7. Findings are stored in `job_security_findings`.
8. Compile creates a digest with `agent_session_id`.
9. `clawguard_post_compile.sh` queries findings for that session and writes telemetry artifacts.

## Trust Boundaries

| Boundary | Untrusted Side | Trusted/Controlled Side | Control |
|---|---|---|---|
| Job source ingestion | Job postings and search snippets | OpenClaw runtime | Treat external content as data |
| Detector boundary | Job text and apply URLs | ASI06, ASI01, and ASI02 detector rules | Evidence-preserving findings |
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
| ASI01 status | Corroborated detector v1 | Pure regex scanner or wait for live attack only | Adds goal-impact interpretation without duplicating ASI06 | Ambiguous semantic cases still need future review layer |
| ASI02 status | Content-side detector v1 | Runtime tool-call monitor first | Catches unsafe tool-use instructions before action | Does not yet observe actual tool calls |

## Implemented Guardrails

- ASI06 content checks for prompt injection, PII requests, skill stuffing, and URL mismatch.
- ASI01 goal-redirect classification using ASI06 prompt-injection findings as upstream signal.
- ASI02 tool-misuse classification for unsafe egress, notification redirects, shell payloads, and file-write redirects.
- `agent_session_id` correlation.
- Cron disables application auto-prep.
- `.env.example` placeholders; `.env` ignored.
- Post-compile telemetry only after successful digest compile.

## Recommended (not implemented here)

- Runtime tool-call instrumentation for ASI02 Layer 3/4 detection.
- Prompt sanitization or quarantine before future LLM summarization.
- LLM-as-judge guardrail for ambiguous ASI01 cases.
- Signed deployment bundle for the OpenClaw script and `detections/` package.
- CI/CD packaging for VPS deployment.
