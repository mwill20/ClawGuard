# Phase 4 Spec - Runtime Detector Promotion

Last updated: 2026-05-07
Status: In progress; local detector promotion complete, scheduled runtime confirmation pending
Predecessor: Phase 3 runtime-event monitoring and curated clean baselines

## Mission

Phase 4 promotes runtime-event evidence into ASI03 and ASI05 detectors. The goal
is not to block behavior. The goal is to produce reviewer-grade findings from
validated, redacted runtime facts while keeping normal cron/search/deploy
behavior clean.

```text
Phase 3: emit facts
Phase 4: classify facts
```

## Starting Baseline

Implemented before Phase 4:

- `runtime-events/0.1` writer and validator.
- Python runtime hooks for `identity_context`, `credential_use`,
  `network_egress`, and `file_write`.
- Host wrapper annotations for `process_exec` and `container_action`.
- Host-side redaction before export.
- Curated clean runtime-event baselines:
  - `digest-20260507T041020-50c7d030` validates `--require asi03`.
  - `digest-20260507T174059-2121b8be` validates `--require asi03 --require asi05`.
- `examples/runtime_events_normal_ops.json` clean false-positive fixture.
- False-positive expectations in
  `docs/plans/PHASE3_FALSE_POSITIVE_EXPECTATIONS.md`.
- Local-only ASI03/ASI05 positive fixtures and runtime detectors.

## Phase 4 Tracks

### Track A - Scheduled Runtime Confirmation

Goal: verify the next scheduled cron emits runtime events without manual
intervention.

Acceptance criteria:

- Daily digest email still sends.
- Telemetry still validates as schema `1.2`.
- Scheduled runtime-event artifact exists for the scheduled session.
- Artifact validates under `runtime-events/0.1`.
- If the scheduled run has real jobs, ASI06/ASI01/ASI02 activation lines remain present.

Blocker note: the May 7 scheduled cron completed before
`CLAWGUARD_RUNTIME_EVENTS_ENABLED=1` was fixed on the host. A real no-notify
run already proved the runtime-event path, but scheduled proof remains pending
until the next daily run.

### Track B - Local Positive Runtime Fixtures

Goal: create local-only positive samples for ASI03 and ASI05. These must never
be sent to live providers.

Candidate files:

```text
examples/runtime_events_asi03_positive.json
examples/runtime_events_asi05_positive.json
examples/runtime_events_asi03_asi05_combined.json
```

Status: done.

Acceptance criteria:

- Fixtures validate under `runtime-events/0.1`.
- Fixtures contain only labels, hashes, and redacted placeholders.
- Fixtures model attacks as runtime events, not job descriptions.
- Clean baselines remain separate and unchanged.

### Track C - ASI03 Runtime Detector v1

Goal: detect identity and privilege abuse from runtime events.

Module:

```text
detections/asi03_identity_abuse/detector.py
```

Status: done for the first two v1 rules.

Initial rule families:

| Rule ID | Trigger | Required safe evidence |
|---|---|---|
| `ASI03_UNKNOWN_CREDENTIAL_LABEL` | Credential label outside approved provider/deploy inventory | credential label, event_id, session_id |
| `ASI03_CREDENTIAL_EGRESS_MISMATCH` | Credential use followed by egress to non-approved destination | credential label, destination domain label, related event IDs |
| `ASI03_IDENTITY_CONTEXT_SWITCH` | Identity context changes outside approved workflow reason | old/new identity labels, reason label, event IDs |
| `ASI03_SECRET_PATH_ACCESS` | Secret path label accessed outside approved profile/config labels | path label, actor label, policy decision |

Acceptance criteria:

- Clean Phase 3 baselines produce zero ASI03 findings.
- Positive local-only ASI03 fixture produces expected findings.
- Findings contain no raw secrets, raw paths, host IDs, or tokens.
- Detector output can be converted to a reviewer record with `to_record()`.

### Track D - ASI05 Runtime Detector v1

Goal: detect unexpected code execution from runtime events.

Module:

```text
detections/asi05_code_execution/detector.py
```

Status: done for the first two v1 rules.

Initial rule families:

| Rule ID | Trigger | Required safe evidence |
|---|---|---|
| `ASI05_UNAPPROVED_PROCESS_LABEL` | Process label outside approved inventory | process label, actor label, event_id |
| `ASI05_UNTRUSTED_CONTENT_EXECUTION` | Process/action label derived from untrusted content | source label, command label, related job/content ID if safe |
| `ASI05_UNAPPROVED_CONTAINER_ACTION` | Container action outside cron/deploy labels | container label, operation label, event_id |
| `ASI05_SENSITIVE_FILE_MUTATION` | File write targets cron/deploy/runtime config label outside deploy workflow | path label, actor label, policy decision |

Acceptance criteria:

- Clean Phase 3 baselines produce zero ASI05 findings.
- Positive local-only ASI05 fixture produces expected findings.
- Findings contain no raw command lines, raw args, host IDs, container IDs, private paths, or secrets.
- Detector does not duplicate ASI02 content-side shell detection.

### Track E - Evaluation and CI

Goal: make runtime detector behavior mechanically reproducible.

Acceptance criteria:

- Add unit tests for ASI03 and ASI05 detectors.
- Add evaluator scripts or one combined runtime detector evaluator.
- Add preflight steps for clean baseline zero-findings and positive fixture metrics.
- Add CI steps mirroring preflight.
- Keep stale test-count guard current.

Status: done with `scripts/evaluate_runtime_detectors.py`, preflight, and CI.

### Track F - Persistence Decision

Goal: decide whether runtime findings should be persisted in SQLite.

Default Phase 4 posture:

- Start with evaluator JSON output and tests.
- Do not add a DB migration until detector outputs stabilize.
- If persistence is needed, prefer a separate `runtime_security_findings` table
  keyed by `agent_session_id` and `event_id`, not `job_id`.

Status: deferred. ASI03/ASI05 currently remain evaluator/file based with no
SQLite migration.

## Non-Goals

- No live-provider synthetic malicious jobs.
- No blocking or enforcement.
- No raw secrets, raw commands, private paths, host identifiers, or container IDs in findings.
- No ASI03 detector over job-description text.
- No ASI05 detector that duplicates ASI02 content-side shell detection.

## Phase 4 Exit Criteria

Phase 4 can close when:

1. Scheduled runtime-event emission is confirmed.
2. ASI03 and ASI05 positive fixtures exist and validate locally.
3. Clean runtime baselines produce zero ASI03/ASI05 findings.
4. Positive fixtures produce expected ASI03/ASI05 findings.
5. Evaluator metrics are wired into preflight and CI.
6. Detector docs and lessons explain what is implemented versus recommended.
7. Persistence is either implemented safely or explicitly deferred with rationale.

## Open Decisions

- Should ASI03 and ASI05 share one runtime detector adapter or use separate
  modules with a common result dataclass?
- Are policy fields on each event sufficient, or should Phase 4 add standalone
  `policy_decision` events?
- Should runtime findings stay file-based for one phase before adding SQLite?
- Which real clean sessions should become permanent false-positive regression
  fixtures?
