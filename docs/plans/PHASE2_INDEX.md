# Phase 2 Plans — Index

Last updated: 2026-05-04

Phase 1 closed with the OpenClaw telemetry baseline, the ASI06 detection module, ASI01 v1, and digest-source-status clarity. Phase 2 expands the detection engine and matures the telemetry pipeline.

## Phase 2 Goals

1. **ASI02 Tool Misuse detection** — extend the detection engine to catch attempts at directing the agent to tools or destinations outside its intended scope. v1 uses content-based pre-action checks; Phase 3 will add tool-call instrumentation.

2. **Curated telemetry export workflow** — formalize the VPS → repo telemetry pipeline so review artifacts ship without manual export and without auto-pushing operational logs.

## Plan Documents

| Document | Scope |
|---|---|
| [PHASE2_ASI02_SPEC.md](PHASE2_ASI02_SPEC.md) | ASI02 detection module — threat model, rule set, integration, tests |
| [PHASE2_TELEMETRY_WORKFLOW.md](PHASE2_TELEMETRY_WORKFLOW.md) | Telemetry export workflow — selection, redaction, schema versioning, automation |

## Sequencing

Phase 2 work is parallelizable. Recommended order:

1. ASI02 spec is approved before any code is written (this doc set is the spec).
2. Telemetry workflow lands first because it produces the artifacts needed to evaluate ASI02 false-positive rates on real-world content.
3. ASI02 v1 ships with synthetic fixture coverage similar to ASI06's `examples/asi06_labeled_eval.json`.
4. Live ASI02 confirmation requires a real signal (just like ASI01 did). Until then, ASI02 is silent.

## Out of Scope for Phase 2

These are deferred to Phase 3:

- Real-time tool-call instrumentation hooks in the OpenClaw runtime (needed for Layer 3/4 ASI02 detection).
- `search_runs` schema migration to persist `source_status`, `already_known_count`, and structured error codes (Phase 1 added these to the audit log only).
- ASI03–ASI05 / ASI07+ rule modules.
- A web UI for telemetry triage.
