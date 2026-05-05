# ClawGuard + OpenClaw Project Spec v2 - Historical Redacted Snapshot

Original date: 2026-03-23
Redaction/update date: 2026-05-05
Status: Superseded historical artifact
Current source of truth: `docs/plans/PHASE2_SPEC.md`

## Historical Note

This file is intentionally retained as a March 2026 time capsule. It captured the project just after the initial OpenClaw deployment, before the current Phase 1 implementation existed.

It is no longer an operational runbook and should not be used for current deployment commands.

Deployment identifiers from the original v2 spec were redacted because tracked specs should not expose live host details, container names, user IDs, filesystem paths, or access commands.

## What v2 Accurately Captured at the Time

- ClawGuard would use a live OpenClaw deployment as a realistic telemetry target.
- The repo would use a single-repository layout with `target-agent/`, `detections/`, and `lessons/`.
- Community job-search skills were not suitable, so the project would write a custom skill.
- Guardrails-first design was the core architecture decision.
- Early attack-surface findings mapped to ASI01, ASI02, ASI03, ASI05, and supply-chain risk.

## Forward Action Tracker Audit

All v2 forward actions are now resolved or superseded:

| v2 item | v2 status | Current status |
|---|---|---|
| Clean up accidental `.git` | NEXT | Done or superseded |
| Push repo scaffold to GitHub | NEXT | Done; repo has active history |
| Write custom job search skill | BUILD | Done; `job_search_secure.py` is live |
| Configure job hunting agent | PENDING | Done; daily maintenance cron is active |
| Design first ClawGuard detection | PENDING | Done; ASI06 and ASI01 runtime modules exist |
| Write lessons entries | ONGOING | Done for Phase 1; lessons continue as project docs |

## What Current Phase 1 Added Beyond v2

- Brave and USAJobs zero-credit paths; Oxylabs disabled in maintenance mode.
- `agent_session_id` as the correlation anchor.
- Post-compile telemetry hook with atomic writes.
- Importable `ASI06JobContentDetector` and `ASI01GoalHijackDetector` modules.
- SQLite-backed `job_security_findings` with structured evidence and context.
- ASI06 URL mismatch rule.
- Source-status audit semantics: `OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR`.
- GitHub Actions CI.
- `preflight.ps1` and cron-confirmation helpers.
- 21 local tests across runtime, detectors, evaluation, telemetry, and privacy behavior.
- `CLAWGUARD_PROFILE_PATH` for private profile separation.
- Full repo readiness docs: evaluation, dataset, model card, monitoring, limitations, lessons.

## Current Phase 2 Direction

The old v2 spec should not be edited into a live plan. Current Phase 2 work is defined in:

- `docs/plans/PHASE2_SPEC.md`
- `docs/plans/PHASE2_ASI02_SPEC.md`
- `docs/plans/PHASE2_TELEMETRY_WORKFLOW.md`

Current Phase 2 priorities:

1. ASI02 tool-misuse detector v1.
2. Telemetry schema versioning and curated export workflow.
3. Redaction-tested curated telemetry artifacts.
4. ASI02 fixture evaluation and red-team lab.
5. ASI03 and ASI05 roadmap specs with implementation prerequisites.

## Security Handling

Do not restore operational identifiers to this file. If deployment-specific details are needed, keep them in local environment variables, private deployment notes, or operator-only scripts.
