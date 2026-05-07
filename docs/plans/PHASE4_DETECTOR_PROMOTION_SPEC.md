# Phase 4 - ASI03/ASI05 Detector Promotion Spec

Last updated: 2026-05-07
Status: Draft design; no Phase 4 detector code implemented yet
Input docs:

- `docs/plans/PHASE4_SPEC.md`
- `docs/plans/PHASE3_FALSE_POSITIVE_EXPECTATIONS.md`
- `docs/plans/PHASE2_RUNTIME_TELEMETRY_CONTRACT.md`

## Purpose

This document defines the first implementation slice for ASI03 and ASI05
runtime detectors. It keeps the detectors evidence-first, local-testable, and
safe to review.

## Detector Input

Runtime detectors should consume the same payload shape validated by
`scripts/validate_runtime_events.py`:

```json
{
  "schema_version": "runtime-events/0.1",
  "generated_at": "2026-05-07T17:40:59Z",
  "agent_session_id": "digest-20260507T174059-2121b8be",
  "events": []
}
```

Do not read live VPS files directly from detector modules. Tests and evaluators
should pass payload dictionaries or fixture paths.

## Recommended Module Layout

```text
detections/asi03_identity_abuse/
  __init__.py
  detector.py
  README.md
  ASI03-001.md
  ASI03-002.md

detections/asi05_code_execution/
  __init__.py
  detector.py
  README.md
  ASI05-001.md
  ASI05-002.md

scripts/evaluate_runtime_detectors.py
tests/test_asi03_runtime_detector.py
tests/test_asi05_runtime_detector.py
```

Use the ASI06/ASI01/ASI02 pattern: detector classes return finding objects with
a `to_record()` method, but do not wire persistence until output is stable.

## Shared Finding Shape

Recommended fields:

| Field | Purpose |
|---|---|
| `rule_id` | Stable detector rule ID, e.g. `ASI03_UNKNOWN_CREDENTIAL_LABEL` |
| `severity` | `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `message` | Reviewer-facing explanation |
| `event_ids` | Runtime event IDs that support the finding |
| `agent_session_id` | Session correlation anchor |
| `evidence` | Label-only facts; no raw secrets/commands/paths |
| `context` | Schema version, detector version, source artifact metadata |

Recommended evidence keys:

```json
{
  "event_id": "evt-digest-...-001",
  "event_type": "credential_use",
  "actor_id": "openclaw-job-search",
  "operation": "credential_use",
  "target_label": "unknown-provider-credential",
  "policy_decision": "review",
  "raw_secret_stored": false
}
```

## ASI03 v1 Rule Design

### ASI03_UNKNOWN_CREDENTIAL_LABEL

Trigger:

- `event_type == "credential_use"`
- Credential target/label is not in the approved baseline inventory.

Severity:

- `MEDIUM` by default.
- `HIGH` if followed by non-approved network egress in the same session.

False-positive guard:

- Approved labels from `PHASE3_FALSE_POSITIVE_EXPECTATIONS.md` must stay clean.

### ASI03_CREDENTIAL_EGRESS_MISMATCH

Trigger:

- A credential-use event appears in the same session as network egress to a
  destination outside the approved provider domains.

Severity:

- `HIGH`.

Evidence:

- credential event ID
- egress event ID
- credential label
- destination domain label

### Deferred ASI03 Rules

- `ASI03_IDENTITY_CONTEXT_SWITCH`
- `ASI03_SECRET_PATH_ACCESS`
- `ASI03_SCOPE_ESCALATION`

Reason: Phase 3 baselines do not yet include enough identity-switch or
file-access variety to implement these without weak assumptions.

## ASI05 v1 Rule Design

### ASI05_UNAPPROVED_PROCESS_LABEL

Trigger:

- `event_type == "process_exec"`
- `operation` or target label is outside the approved process inventory.

Severity:

- `MEDIUM` by default.
- `HIGH` if policy is `review` or if the source label indicates untrusted input.

False-positive guard:

- `cron-wrapper-search-run` and `cron-wrapper-compile-run` must stay clean.

### ASI05_UNAPPROVED_CONTAINER_ACTION

Trigger:

- `event_type == "container_action"`
- Container operation label is outside cron/deploy approved labels.

Severity:

- `HIGH` if action implies runtime mutation.
- `MEDIUM` for unexpected read-only labels.

Evidence:

- container label
- operation label
- event ID
- policy decision

### Deferred ASI05 Rules

- `ASI05_UNTRUSTED_CONTENT_EXECUTION`
- `ASI05_SENSITIVE_FILE_MUTATION`
- `ASI05_CRON_MODIFICATION`

Reason: these require richer event source labels or file mutation summaries
than Phase 3 currently emits.

## Fixture Plan

Clean fixtures:

```text
examples/runtime_events_normal_ops.json
lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/runtime_events.json
lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json
```

Positive local-only fixtures:

```text
examples/runtime_events_asi03_positive.json
examples/runtime_events_asi05_positive.json
examples/runtime_events_asi03_asi05_combined.json
```

Required evaluator behavior:

- Clean fixtures produce zero findings.
- ASI03 positive fixture produces only expected ASI03 rule IDs.
- ASI05 positive fixture produces only expected ASI05 rule IDs.
- Combined fixture produces both expected families.
- Output includes exact-match and micro precision/recall/F1.

## Preflight/CI Gates

Add steps only after detector tests pass locally:

```powershell
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_asi03_positive.json --expected-micro-f1 1.0 --hide-timing
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_asi05_positive.json --expected-micro-f1 1.0 --hide-timing
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_asi03_asi05_combined.json --expected-micro-f1 1.0 --hide-timing
```

Also add clean-baseline zero-finding checks:

```powershell
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_normal_ops.json --expect-no-findings
python -B scripts\evaluate_runtime_detectors.py --input lessons\runtime-events\2026-05\digest-20260507T174059-2121b8be\runtime_events.json --expect-no-findings
```

## Persistence Gate

Do not write ASI03/ASI05 runtime findings to SQLite until:

1. Clean and positive fixture behavior is stable.
2. The finding shape is reviewed.
3. A migration plan exists.
4. The table is session/event based, not job based.

Preferred future table:

```text
runtime_security_findings(
  id,
  agent_session_id,
  event_id,
  rule_id,
  severity,
  message,
  evidence_json,
  context_json,
  detected_at
)
```

## Safety Requirements

- No raw secrets.
- No raw command lines.
- No private paths.
- No host identifiers.
- No container IDs.
- No synthetic malicious jobs in live providers.
- No blocking/enforcement in Phase 4 v1.

## First Build Slice

1. Add `examples/runtime_events_asi03_positive.json`.
2. Add `detections/asi03_identity_abuse/detector.py` with the two v1 ASI03 rules.
3. Add ASI03 tests proving clean baselines stay clean.
4. Add `examples/runtime_events_asi05_positive.json`.
5. Add `detections/asi05_code_execution/detector.py` with the two v1 ASI05 rules.
6. Add ASI05 tests proving clean baselines stay clean.
7. Add combined evaluator only after both detector modules pass independently.
