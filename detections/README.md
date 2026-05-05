# ClawGuard Detections

Detection modules for OWASP Agentic Top 10 threats. Each detection targets a specific attack class with mapped telemetry signals.

## Phase 1 Targets

| Module | OWASP Code | Status |
|---|---|---|
| Goal Hijack Detection | ASI01 | Detector-backed runtime v1 |
| Tool Misuse Detection | ASI02 | Planned |
| JD Content Detection | ASI06 | Detector-backed runtime |

## Detection Architecture

Each detection module follows the 5-layer defense-in-depth pattern:

1. **Regex** - Fast pattern matching for known-bad indicators
2. **AST** - Structural analysis of agent actions
3. **ShellGuard** - Shell command classification and enforcement
4. **LLM** - Semantic analysis for novel/ambiguous threats
5. **SOC Ledger** - Logging, correlation, and human review

## Current Modules

- `asi01_goal_hijack/detector.py` implements ASI01 v1 goal-redirect classification using ASI06 prompt-injection findings as upstream signal.
- `asi01_goal_hijack/ASI01-001.md` documents the first goal-redirection rule unlocked by three clean telemetry sessions.
- `asi06_jd_content/detector.py` implements the ASI06 job-description content detector.
- `asi06_jd_content/ASI06-001.md` documents the prompt-injection rule now backed by the detector module in `job_search_secure.py`.
- `asi06_jd_content/README.md` defines the event schema, baseline, and extraction criteria.
- `job_security_findings` now stores `job_id`, `agent_session_id`, structured `context`, and JSON evidence.

OpenClaw imports the ASI06 and ASI01 detector modules directly. The `detections/` package is a required deployment dependency after the 2026-05-04 VPS redeploy and cron confirmation.

The first clean baseline is `digest-20260502T143953-c9eb7f4c`: 22 jobs evaluated, 0 ASI06 findings. The first autonomous cron-chain baseline is `digest-20260503T163003-b91b67e1`.

## Development Guide

Detection modules will be built here as we map real telemetry from the OpenClaw deployment to OWASP threat patterns. See `target-agent/docs/attack-surface-recon.md` for current findings.
