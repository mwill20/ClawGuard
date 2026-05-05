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

## Sequencing

Phase 2 work is parallelizable. Recommended order:

1. Approve [PHASE2_SPEC.md](PHASE2_SPEC.md) as the v3 source of truth.
2. Land telemetry schema versioning and redaction first because those protect every later review artifact.
3. Implement ASI02 v1 with synthetic fixture coverage similar to ASI06's `examples/asi06_labeled_eval.json`.
4. Confirm ASI02 locally and in deployment packaging before waiting for live organic signals.
5. Draft ASI03 and ASI05 roadmap specs after ASI02 tests are green.

## Out of Scope for Phase 2 Runtime

These are deferred to Phase 3 runtime work:

- Real-time tool-call instrumentation hooks in the OpenClaw runtime (needed for Layer 3/4 ASI02 detection).
- `search_runs` schema migration to persist `source_status`, `already_known_count`, and structured error codes (Phase 1 added these to the audit log only).
- ASI03/ASI05 runtime rule modules. Phase 2 may add roadmap specs, but runtime detectors require additional telemetry.
- A web UI for telemetry triage.
