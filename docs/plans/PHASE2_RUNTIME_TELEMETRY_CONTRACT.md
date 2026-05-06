# Phase 2 - Runtime Telemetry Contract for ASI03 and ASI05

Last updated: 2026-05-05
Status: Phase 2 contract; fixture and validator implemented; runtime instrumentation deferred to Phase 3

## Purpose

ASI03 identity abuse and ASI05 unexpected code execution should not become regex-only detectors. They require runtime facts: which identity was active, which credential label was used, which process or container operation ran, which policy decision applied, and how those events map back to `agent_session_id`.

This contract defines the minimum event shape Phase 3 instrumentation must emit before ASI03 or ASI05 runtime detectors are allowed.

## Current Project Implements

- `examples/runtime_events_minimal.json` provides a synthetic, local-only fixture.
- `scripts/validate_runtime_events.py` validates event shape, redaction posture, and ASI03/ASI05 readiness.
- `tests/test_runtime_event_contract.py` covers valid runtime events, session correlation, secret-field rejection, and readiness requirements.
- `scripts/preflight.ps1` and GitHub Actions run the validator.

No live provider is seeded with synthetic events. No runtime hook emits these events yet.

## Event Stream Shape

```json
{
  "schema_version": "runtime-events/0.1",
  "generated_at": "2026-05-05T20:00:00Z",
  "agent_session_id": "digest-20260505T163003-d9133ff9",
  "events": []
}
```

Each event must include:

| Field | Type | Why it exists |
|---|---|---|
| `event_id` | string | Stable event identity for review and dedupe |
| `event_time` | string | Timeline reconstruction |
| `agent_session_id` | string | Correlates runtime activity to digest/findings |
| `event_type` | string | Distinguishes identity, credential, process, container, file, and policy signals |
| `actor` | object | Names the agent, automation, detector, or helper responsible |
| `source` | object | Names the code component that emitted the event |
| `operation` | string | Plain action name |
| `operation_category` | string | Normalized category for detector rules |
| `target` | object | Redacted/label-only target of the action |
| `policy` | object | `allow`, `block`, `observe`, or `review` plus reason |
| `correlation` | object | Session ID and related ASI rule IDs |
| `evidence` | object | Event-specific context that does not store raw secrets |

## Minimum ASI03 Signals

ASI03 readiness requires all of:

1. `identity_context` - what user/service identity was active.
2. `credential_use` - which credential label was read or used, never the raw value.
3. `file_access` or `network_egress` - where identity material could have moved.
4. Policy decision on every event.
5. `agent_session_id` correlation on every event.

Without these signals, ASI03 would confuse job text mentioning secrets with actual credential misuse.

## Minimum ASI05 Signals

ASI05 readiness requires all of:

1. `process_exec` - command label, cwd label, exit code, actor, and policy decision.
2. `container_action` or `file_write` - proof of deployment/container/file mutation surface.
3. Policy decision on every event.
4. `agent_session_id` correlation on every event.
5. Redacted or label-only arguments and targets.

Without these signals, ASI05 would duplicate ASI02 shell-content detection instead of proving execution behavior.

## Redaction Rules

Runtime events must not include raw secrets or deployment identifiers.

The validator rejects keys such as:

- `api_key`
- `password`
- `raw_secret`
- `raw_token`
- `secret_value`
- `token_value`

The validator also rejects common raw credential patterns such as OpenAI-style `sk-...`, GitHub `ghp_...`, Slack `xox...`, AWS `AKIA...`, and private key headers.

Use labels and hashes instead:

```json
{
  "target": {
    "kind": "credential_label",
    "label": "brave-search-provider-credential",
    "redaction_status": "redacted",
    "hash": "sha256:example-redacted-provider-credential-label"
  }
}
```

## Validation Commands

PowerShell:

```powershell
python -B scripts\validate_runtime_events.py --input examples\runtime_events_minimal.json --require asi03 --require asi05
```

Bash:

```bash
python -B scripts/validate_runtime_events.py --input examples/runtime_events_minimal.json --require asi03 --require asi05
```

Expected output:

```json
{
  "agent_session_id": "digest-20260505T163003-d9133ff9",
  "event_count": 7,
  "event_type_counts": {
    "container_action": 1,
    "credential_use": 1,
    "file_write": 1,
    "identity_context": 1,
    "network_egress": 1,
    "policy_decision": 1,
    "process_exec": 1
  },
  "policy_decision_counts": {
    "allow": 4,
    "observe": 2,
    "review": 1
  },
  "required_readiness": [
    "asi03",
    "asi05"
  ],
  "schema_version": "runtime-events/0.1",
  "status": "valid"
}
```

## Phase 3 Implementation Notes

Recommended runtime hook points:

- Wrap provider HTTP calls to emit `network_egress` and credential-label usage.
- Wrap telemetry/file writes to emit `file_write`.
- Wrap deployment and cron helpers to emit `process_exec` and `container_action`.
- Emit `identity_context` once per `agent_session_id`.
- Never persist raw request bodies, raw command arguments, raw paths with private host/user data, or raw credential values.

## Non-Goals

- Do not add ASI03/ASI05 runtime detectors in Phase 2.
- Do not infer credential misuse from job-description text alone.
- Do not inject synthetic malicious jobs into live providers.
- Do not store raw secrets, host identifiers, container names, profile paths, or private user data in runtime events.
