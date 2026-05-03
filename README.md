# ClawGuard

Guardrail-first AI agent security monitoring framework.

ClawGuard detects OWASP Agentic Top 10 risks against AI agents by watching a real OpenClaw deployment, not simulated traces. The current live target is the OpenClaw `job-search-custom` skill running on a VPS and producing low-volume operational telemetry for ClawGuard.

## Current Posture

Last updated: 2026-05-03

ClawGuard is in Phase 1: OpenClaw is stable, the job-search pipeline is intentionally throttled, and the first ClawGuard telemetry path is live.

Active operating model:

- OpenClaw runs daily maintenance searches, not high-volume job application automation.
- Oxylabs is disabled for maintenance mode with `CLAWGUARD_DISABLE_OXYLABS=1`.
- Brave Search and the native USAJobs API provide zero-credit source collection.
- JD enrichment is disabled with `CLAWGUARD_ENRICHMENT_DAILY_CAP=0`.
- Application auto-prep is disabled in cron via `--no-prepare`.
- Post-compile telemetry writes JSON and Markdown summaries under `/data/clawguard/telemetry/`.
- Repo telemetry is curated manually; the VPS remains the continuous operational record.

Current daily schedule on the VPS:

| Time PT | Job |
|---|---|
| 9:00 AM | LinkedIn maintenance search |
| 9:10 AM | CyberSecJobs maintenance search |
| 9:20 AM | USAJobs native API search |
| 9:30 AM | Compile digest and run ClawGuard post-compile telemetry hook |

## What ClawGuard Monitors

ClawGuard maps agent behavior and ingested content to OWASP Agentic Top 10 risks:

| Detection | OWASP Code | Current State |
|---|---|---|
| Goal hijack detection | ASI01 | Scaffolded after three clean OpenClaw telemetry sessions |
| Tool misuse detection | ASI02 | Planned |
| Job-description content detection | ASI06 | Detector-backed runtime with inline fallback |

The active ASI06 path detects suspicious job content such as prompt injection, PII requests, skill stuffing, and suspicious apply-domain mismatches. Findings are persisted to `job_security_findings` with `job_id`, `agent_session_id`, structured `context`, and evidence containing `pattern`, `matched_text`, and `snippet`.

## Architecture

ClawGuard follows a guardrails-first design:

- AI agents are treated as untrusted by default.
- External content is treated as data, not instruction.
- High-risk agent actions require human review.
- Detection events preserve correlation fields for later ClawGuard analysis.
- Operational telemetry is captured continuously but committed only when curated.

Current flow:

```text
OpenClaw cron
  -> job-search-custom searches LinkedIn, CyberSecJobs, USAJobs
  -> SQLite stores jobs, scores, and ASI06 findings
  -> digest compile creates agent_session_id
  -> clawguard_post_compile.sh exports telemetry JSON/Markdown
  -> lessons/ captures curated baselines and review artifacts
```

## Project Structure

```text
ClawGuard/
  ClawGuardSpecs/        ClawGuard specs, runbooks, and foundation docs
  OpenClawSpecs/         OpenClaw target-agent specs and runbooks
  target-agent/          Live OpenClaw deployment docs and custom skills
  detections/            ClawGuard detection rule specs and future modules
  lessons/               Baselines, learning notes, and architecture artifacts
  scripts/               Local helper scripts, including telemetry export
  tests/                 Regression tests for the job-search skill
```

## Key Artifacts

- `PHASE1_PROGRESS.md` - current operational tracker and AI handoff.
- `target-agent/skills/job-search-custom/job_search_secure.py` - live job-search runtime; prefers the ASI06 detector module when packaged, with an inline fallback for single-file deploys.
- `target-agent/skills/job-search-custom/staggered_cron.sh` - daily maintenance schedule driver.
- `target-agent/skills/job-search-custom/clawguard_post_compile.sh` - post-compile telemetry hook.
- `detections/asi06_jd_content/detector.py` - first importable ClawGuard detection engine module.
- `detections/asi06_jd_content/ASI06-001.md` - first ClawGuard detection rule spec.
- `lessons/clawguard-telemetry-baseline-001.md` - first clean telemetry baseline.
- `scripts/export_latest_telemetry.ps1` - manual export path for VPS telemetry samples.

## Latest Baseline

Baseline `digest-20260502T143953-c9eb7f4c` evaluated 22 jobs across LinkedIn and CyberSecJobs with 0 ASI06 findings, 0 auto-prepared applications, and 0 Oxylabs credits used.

Zero findings are meaningful telemetry. They establish a clean-content baseline for detector tuning and future runtime integration.

## Immediate Next Steps

- Let the daily 9:00-9:30 AM PT chain run and accumulate clean sessions.
- After the next full cron chain, review `/data/clawguard/telemetry/telemetry_latest.md`.
- Ship the `detections/` package with the next VPS deploy, verify detector-backed ASI06 findings, then remove the inline fallback.
- Keep ASI01 as a docs-only scaffold until a live redirect signal or ASI06 prompt-injection event appears.
- Keep Oxylabs debugging isolated from the maintenance pipeline.

## Author

Built by Michael Williams, SOC analyst with MSSP background transitioning to AI Security Engineering. GIAC certified, UT Austin AI/ML program graduate.

## License

MIT
