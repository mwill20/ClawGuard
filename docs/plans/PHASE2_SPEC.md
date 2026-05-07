# Phase 2 Spec v3 - Current Baseline and Execution Plan

Last updated: 2026-05-06
Status: Complete; retained as Phase 2 record
Supersedes: `ClawGuardSpecs/ClawGuard_OpenClaw_Project_Spec_v2.md` and the Phase 2 section in `ClawGuardSpecs/CLAWGUARD_PROJECT_SPEC.md`

## Why This Spec Exists

The March 2026 project specs are useful history, but they describe a project that no longer exists. Phase 1 and Phase 2 are closed. The repo now has a live OpenClaw telemetry loop, detector-backed ASI06, ASI01, and ASI02 modules, session-correlated SQLite findings, post-compile telemetry, curated export helpers, runtime-event contract validation, runtime-event writer tests, runtime-event redaction/export tests, normal-ops runtime-event fixture validation, source-health digest reporting, lessons, CI, and 77 local tests.

Phase 2 starts from that baseline. It should not repeat already-completed scaffold work.

## Current Baseline

Phase 1 delivered:

| Area | Current state |
|---|---|
| Runtime | `target-agent/skills/job-search-custom/job_search_secure.py` deployed as the OpenClaw job-search runtime |
| Search posture | Low-volume daily maintenance mode; Brave and USAJobs are zero-credit paths; Oxylabs is disabled for maintenance |
| Detectors | ASI06 job-content detector, ASI01 goal-hijack detector v1, and ASI02 tool-misuse detector v1 are importable runtime modules |
| Persistence | `job_security_findings` stores `job_id`, `agent_session_id`, `rule_id`, `severity`, `message`, JSON `evidence`, JSON `context`, and `detected_at` |
| Digest semantics | Source audit events distinguish `OK_NEW`, `ALL_KNOWN`, `EMPTY`, and `ERROR` |
| Discovery reliability | Daily search expands profile/default role terms, searches primary + Remote locations, uses Brave freshness/pagination, filters aggregate pages, and splits USAJobs OR terms before API calls |
| Telemetry | Post-compile hook writes per-session JSON/Markdown and `_latest` files atomically |
| Testing | 77 tests cover parsers, ASI01/ASI02/ASI06 detectors, persistence, telemetry validation, runtime-event contract and writer behavior, runtime hook emission, runtime-event redaction/export, normal-ops runtime-event fixture validation, review-session selection, export redaction, profile privacy, source-status audit, source-health digest reporting, schema-version branches, and fixture evaluation |
| Ops helpers | `preflight.ps1`, `deploy_openclaw_skill.ps1`, `check_cron_confirmation.ps1`, `check_latest_telemetry.ps1`, `export_telemetry.ps1`, `export_latest_telemetry.ps1` |
| Data separation | `CLAWGUARD_PROFILE_PATH` keeps private profile data outside the repo |

## Phase 2 Mission

Move ClawGuard from "content and goal detection with clean telemetry" to "tool-misuse detection with curated evidence workflows and stronger evaluation discipline."

Phase 2 has four tracks:

1. ASI02 tool-misuse detection v1.
2. Curated telemetry export and schema versioning.
3. Real-world labeled corpus and red-team exercise workflow.
4. ASI03/ASI05 roadmap specs for identity abuse and unexpected code execution.

## Track A - ASI02 Tool Misuse Detection

Primary spec: [PHASE2_ASI02_SPEC.md](PHASE2_ASI02_SPEC.md)

Phase 2 implements content-side, pre-action ASI02 detection. Runtime tool-call instrumentation remains Phase 3 because the current OpenClaw target does not emit structured tool-call events.

Acceptance criteria:

- `detections/asi02_tool_misuse/detector.py` exists and follows the ASI06/ASI01 detector pattern. Done.
- `run_jd_security_detections()` executes ASI06, then ASI01, then ASI02. Done.
- `record_security_findings()` replaces `ASI02_%` findings along with ASI06/ASI01 families. Done.
- ASI02 evidence includes `pattern`, `matched_text`, `snippet`, attempted operation category, and corroboration links when ASI06/ASI01 also fired. Done.
- Clean cybersecurity job content that merely discusses shell, curl, APIs, or prompt injection does not produce HIGH findings without imperative misuse language. Done.
- `scripts/deploy_openclaw_skill.ps1` compiles ASI02 during dry-run and deploy. Done.
- `scripts/check_cron_confirmation.ps1` can report ASI02 module activation without failing before first invocation. Done.
- ASI02 activation has been confirmed on a no-notify compile over real discovered jobs. Done on May 6, 2026.
- Discovery was repaired after the May 6 empty digest, and the live no-notify trial evaluated real jobs before Phase 3 began. Done.

## Track B - Curated Telemetry Workflow

Primary spec: [PHASE2_TELEMETRY_WORKFLOW.md](PHASE2_TELEMETRY_WORKFLOW.md)

Phase 2 formalizes how telemetry moves from the operational host to the repo without auto-pushing logs or leaking sensitive data.

Acceptance criteria:

- Telemetry JSON gains a top-level `schema_version`. Done.
- A structured selector can choose sessions by rule, finding count, date, and clean-baseline status. Done.
- Selection uses a JSON parser, not grep-style parsing. Done.
- Export applies redaction before artifacts land under `lessons/telemetry/`. Done.
- Redaction covers email, phone, private profile strings, deployment identifiers, and configurable additional patterns. Done.
- `scripts/validate_telemetry.py` validates every supported schema version. Done through schema `1.2`.
- Curated exports produce a monthly `index.md` with session IDs, schema version, finding counts, and reviewer notes. Done.

## Track C - Corpus and Red-Team Exercises

Phase 1 has strong synthetic fixtures but no large real-world labeled corpus. Phase 2 should build evaluation assets before claiming real-world precision/recall.

Deliverables:

- `examples/asi02_labeled_eval.json` with clean, single-rule, and combo cases. Done.
- A sanitized real-world review corpus under `lessons/telemetry/` or `examples/curated/`. First clean baseline exported; finding-bearing/false-positive samples still pending.
- A red-team lab that exercises ASI06, ASI01, and ASI02 together without touching live job providers. Done for local synthetic runtime-chain workflow; curated real-world lab still pending.
- A documented confusion-matrix workflow for synthetic and curated sets. Done for synthetic ASI02 results and clean-baseline telemetry interpretation; finding-bearing curated workflow still pending.

Acceptance criteria:

- Preflight includes ASI02 fixture evaluation. Done.
- `docs/EVALUATION.md` separates synthetic fixture metrics from curated real-world review notes. Done.
- No live provider is polluted with synthetic attacker URLs or fake job content.

## Track D - ASI03 and ASI05 Roadmap Specs

The March spec listed ASI03 identity/privilege abuse and ASI05 unexpected code execution as Phase 2 hardening items. They still matter, but runtime implementation should wait for the right telemetry.

Phase 2 deliverables:

- `docs/plans/PHASE2_ASI03_IDENTITY_SPEC.md` as a scaffold spec only. Done.
- `docs/plans/PHASE2_ASI05_CODE_EXEC_SPEC.md` as a scaffold spec only. Done.
- `docs/plans/PHASE2_RUNTIME_TELEMETRY_CONTRACT.md` as the minimum event contract for future ASI03/ASI05 runtime instrumentation. Done.
- `examples/runtime_events_minimal.json`, `scripts/validate_runtime_events.py`, and `tests/test_runtime_event_contract.py` as a local-only validation harness. Done.
- Clear prerequisites for implementation, such as structured credential-use events, tool-call logs, process/container telemetry, or deployment config snapshots.

Non-goal:

- Do not build speculative ASI03/ASI05 runtime detectors from regexes alone.

## Historical Spec Hygiene

The March v2 spec is tracked, so it must be treated as a historical artifact, not an operational runbook.

Rules for historical specs:

- Mark superseded specs clearly.
- Redact deployment identifiers from specs intended to be public.
- Do not store private hostnames, user IDs, IPs, filesystem paths, tokens, or real profile data in phase specs.
- Keep operational values in local environment variables, private notes, or deployment-only scripts.

## Phase 2 Decision Gates

| Gate | Decision | Default |
|---|---|---|
| D1 | ASI02 safe egress domains | Start strict: Brave API, USAJobs API, LinkedIn, USAJobs, CyberSecJobs. Do not treat arbitrary apply URLs as safe command-fetch targets. |
| D2 | Shell-injection severity | MEDIUM for bare snippets; HIGH only when paired with imperative execute/fetch/send language or a dangerous sink. |
| D3 | Redaction location | Local-side redaction first for speed; revisit host-side redaction before any automation. |
| D4 | ASI03/ASI05 scope | Specs only in Phase 2 unless structured runtime telemetry appears. |
| D5 | Live confirmation | Use local/staging synthetic fixtures; do not inject fake attacker jobs into live job providers. |
| D6 | ASI02 score impact | Review-only in Phase 2; persist and export findings, but do not reduce job score until real false-positive behavior is measured. |

## Phase 2 Exit Criteria

Phase 2 is complete when:

1. ASI02 v1 is implemented, tested, deployable, and cron-confirmable.
2. Telemetry schema versioning and curated export workflow are implemented.
3. Redaction is tested before curated artifacts enter the repo.
4. ASI02 synthetic fixture evaluation is wired into preflight.
5. At least one sanitized curated telemetry set exists for reviewer learning. Done for clean baseline.
6. ASI03 and ASI05 have scoped roadmap specs with a validated runtime-event contract for implementation prerequisites.
7. Lessons are updated with the bot-detection-to-agent-monitoring analogy and the ASI02 defense lab.

## Immediate Next Actions

1. Add a finding-bearing or false-positive curated telemetry sample when real telemetry warrants it.
2. Expand the ASI02 defense lab with curated real-world false-positive examples.
3. Watch the next scheduled digest after the discovery fix and compare delivered matches against the no-notify preview baseline.
