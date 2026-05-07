# Phase 3 Spec - Runtime Event Instrumentation and Detector Promotion

Last updated: 2026-05-07
Status: Complete for instrumentation, redaction, validation, and curated baselines; ASI03/ASI05 detector implementation moves to Phase 4
Predecessor: Phase 2 ASI02 detector, curated telemetry workflow, and `runtime-events/0.1` contract

## Mission

Phase 3 moves ClawGuard from content-side detection to runtime-observed agent behavior. The first deliverable is not ASI03 or ASI05 findings. The first deliverable is trustworthy runtime event emission with redaction, validation, and session correlation.

## Starting Baseline

Implemented before Phase 3:

- ASI06, ASI01, and ASI02 runtime detectors.
- `job_security_findings` persistence keyed by `agent_session_id`.
- Post-compile telemetry JSON/Markdown with schema `1.2`.
- Curated telemetry selection, redaction, validation, and export helpers.
- Combined ASI06 + ASI01 + ASI02 synthetic detector-chain lab.
- `runtime-events/0.1` schema fixture and validator.
- Deploy helper ships runtime, detections, post-compile hook, and cron wrapper.
- Email compile path verified after `CLAWGUARD_EMAIL_TO` forwarding fix.
- May 6 live no-notify digest trial evaluated real jobs and confirmed ASI02 activation.
- May 7 UTC one-off observe-only runtime-event baselines validated on the VPS with runtime events disabled by default outside the test runs.
- May 7 UTC host-side runtime-event redaction deployed before any export path.
- Host-side runtime-event annotation deployed for label-only cron wrapper `process_exec` and `container_action` events.
- Clean ASI03-ready runtime-event baseline curated at `lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/`.
- Clean ASI03/ASI05-ready no-notify provider baseline curated at `lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/`.

## Phase 3 Tracks

### Track A - Operational Readiness

Goal: make sure the daily system is healthy before adding new runtime signals.

Acceptance criteria:

- May 6 scheduled compile runs at 9:30 AM PT.
- Email delivery succeeds from the scheduled compile.
- `telemetry_latest.json` validates as schema `1.2`.
- ASI02 activation is confirmed only if a real compile evaluates jobs.
- No synthetic malicious jobs are inserted into live providers.

Primary runbook: [PHASE3_TOMORROW_RUNBOOK.md](PHASE3_TOMORROW_RUNBOOK.md)

### Track B - Runtime Event Emission

Goal: emit `runtime-events/0.1` records in observe-only mode.

Required event types:

- `identity_context`
- `credential_use`
- `network_egress`
- `file_write`
- `process_exec`
- `container_action`
- Policy decisions as event fields; standalone `policy_decision` event documents are deferred to detector work if needed.

Acceptance criteria:

- Runtime event files validate with `scripts/validate_runtime_events.py`.
- No raw secrets, raw tokens, private host identifiers, raw command args, or profile paths are stored.
- Every event has `agent_session_id`.
- Events are correlated to digest and telemetry sessions.
- Preflight includes at least one runtime-event validation fixture.

Primary spec: [PHASE3_RUNTIME_INSTRUMENTATION_SPEC.md](PHASE3_RUNTIME_INSTRUMENTATION_SPEC.md)

### Track C - Host-Side Redaction

Goal: prepare for future automation without moving sensitive data off-host first.

Acceptance criteria:

- Host-side redaction runs before any automated export. Done with `clawguard_redact_runtime_events.py` deployed on the VPS host.
- Local validation remains as a second layer after transfer. Done in `scripts/export_runtime_events.ps1`.
- Redaction tests cover runtime-event artifacts. Done in `tests/test_export_redaction.py`.
- Export artifacts include redaction status and schema version. Done for the first clean baseline.

### Track D - ASI03/ASI05 Detector Promotion

Goal: promote ASI03 and ASI05 from roadmap specs to runtime detectors only after runtime events exist.

Promotion gates:

- At least one clean runtime-event baseline exists. Done.
- At least one real review-worthy runtime-event sample exists, or a local-only synthetic fixture clearly models the rule without touching live providers. Done for clean no-notify provider behavior; positive detector fixtures move to Phase 4 and must remain local-only.
- False-positive expectations exist for normal cron/deploy/search behavior. Done in [PHASE3_FALSE_POSITIVE_EXPECTATIONS.md](PHASE3_FALSE_POSITIVE_EXPECTATIONS.md), with executable clean-fixture validation in `examples/runtime_events_normal_ops.json`.
- Findings never persist raw credentials, command args, private paths, or host identifiers.

Non-goals:

- No ASI03 regex scanner over job text.
- No ASI05 detector that duplicates ASI02 shell-content detection.
- No blocking/enforcement before observe-only telemetry is stable.

## Phase 3 Exit Criteria

Phase 3 is complete when:

1. Runtime events are emitted in observe-only mode.
2. Runtime events validate under `runtime-events/0.1`.
3. Host-side redaction exists before automated export.
4. Curated runtime-event baselines exist for reviewer learning.
5. ASI03/ASI05 detector promotion gates are either satisfied or explicitly deferred with evidence.
6. Lessons and evaluation docs explain runtime-event monitoring and ASI03/ASI05 readiness.

## First Implementation Slice

Start with event plumbing, not new findings:

1. Add a runtime-event writer that can emit session JSON under `/data/clawguard/runtime_events/`. Done.
2. Emit one `identity_context` event per digest session. Done in Python runtime hooks.
3. Emit provider `network_egress` and credential-label events from Brave/USAJobs calls. Done in Python runtime hooks.
4. Emit file-write events for digest/runtime-event writes. Digest output and runtime-event self-write are done; telemetry and application-material file-write events remain deferred because post-compile telemetry is host-side and auto-prepare did not run in the clean baseline.
5. Extend validation/export helpers for runtime-event artifacts. Done with host-side redaction, local validation, and curated export into `lessons/runtime-events/`.
6. Add label-only host-wrapper `process_exec` and `container_action` annotation. Done via `clawguard_annotate_runtime_events.py` and `staggered_cron.sh`.
7. Keep all runtime-event emission observe-only. Required.

## Current Runtime-Event Baselines

The first curated runtime-event baseline is intentionally clean and observe-only:

```text
lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/
```

It came from a read-only USAJobs provider smoke run that emitted `identity_context`, `credential_use`, `network_egress`, and `file_write` events. It is suitable for reviewer learning and ASI03 readiness discussion, but it is not a finding-bearing sample and should not be used to claim ASI03/ASI05 detector readiness.

The full clean no-notify provider baseline is:

```text
lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/
```

It emitted 162 host-redacted events: `identity_context`, `credential_use`,
`network_egress`, `file_write`, `process_exec`, and `container_action`. It
validates with:

```powershell
python -B scripts\validate_runtime_events.py --input lessons\runtime-events\2026-05\digest-20260507T174059-2121b8be\runtime_events.json --require asi03 --require asi05
```

It is still a clean observe-only baseline. It proves readiness coverage for
ASI03/ASI05 detector design, not a promoted runtime finding.
