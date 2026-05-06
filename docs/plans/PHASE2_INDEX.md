# Phase 2 Plans - Index

Last updated: 2026-05-05

Phase 1 closed with the OpenClaw telemetry baseline, ASI06 detector module, ASI01 v1, and digest-source-status clarity. Phase 2 expands the detection engine and matures the telemetry pipeline.

## Phase 2 Goals

1. **ASI02 Tool Misuse detection** - extend the detection engine to catch attempts at directing the agent to tools or destinations outside its intended scope. v1 uses content-based pre-action checks; Phase 3 will add tool-call instrumentation.

2. **Curated telemetry export workflow** - formalize the operational-host-to-repo telemetry pipeline so review artifacts ship without manual export and without auto-pushing operational logs.

3. **Evaluation and red-team discipline** - build ASI02 fixtures, curated real-world review samples, and a red-team lab that does not pollute live providers.

4. **ASI03/ASI05 roadmap specs** - scope identity abuse and unexpected code execution work without building speculative detectors before telemetry exists.

## Plan Documents

| Document | Scope |
|---|---|
| [PHASE2_SPEC.md](PHASE2_SPEC.md) | Phase 2 v3 umbrella spec - current baseline, tracks, gates, exit criteria |
| [PHASE2_ASI02_SPEC.md](PHASE2_ASI02_SPEC.md) | ASI02 detection module - threat model, rule set, integration, tests |
| [PHASE2_TELEMETRY_WORKFLOW.md](PHASE2_TELEMETRY_WORKFLOW.md) | Telemetry export workflow - selection, redaction, schema versioning, automation |
| [PHASE2_ASI03_IDENTITY_SPEC.md](PHASE2_ASI03_IDENTITY_SPEC.md) | ASI03 identity and privilege abuse roadmap - prerequisites, signals, non-goals |
| [PHASE2_ASI05_CODE_EXEC_SPEC.md](PHASE2_ASI05_CODE_EXEC_SPEC.md) | ASI05 unexpected code execution roadmap - prerequisites, signals, non-goals |
| [PHASE2_RUNTIME_TELEMETRY_CONTRACT.md](PHASE2_RUNTIME_TELEMETRY_CONTRACT.md) | Minimum runtime-event schema for future ASI03/ASI05 detectors |

## Sequencing

Phase 2 work is parallelizable. Recommended order:

1. Approve [PHASE2_SPEC.md](PHASE2_SPEC.md) as the v3 source of truth.
2. Land telemetry schema versioning and redaction first because those protect every later review artifact.
3. ASI02 v1 and synthetic fixture coverage are implemented; deploy and cron-confirm after first invocation.
4. ASI03 and ASI05 roadmap specs are drafted, and the runtime-event contract defines the minimum Phase 3 signals.
5. ASI02 defense lab and combined detector-chain fixture are added; next add finding-bearing or false-positive curated telemetry when real sessions warrant it.

## Out of Scope for Phase 2 Runtime

These are deferred to Phase 3 runtime work:

- Real-time tool-call instrumentation hooks in the OpenClaw runtime (needed for Layer 3/4 ASI02 detection).
- `search_runs` schema migration to persist `source_status`, `already_known_count`, and structured error codes (Phase 1 added these to the audit log only).
- ASI03/ASI05 runtime rule modules. Phase 2 may add roadmap specs, but runtime detectors require additional telemetry.
- A web UI for telemetry triage.
