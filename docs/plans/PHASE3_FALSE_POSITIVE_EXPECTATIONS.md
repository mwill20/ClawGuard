# Phase 3 - ASI03/ASI05 False-Positive Expectations

Last updated: 2026-05-07
Status: Active promotion gate; ASI03/ASI05 detectors are not implemented yet

## Purpose

ASI03 and ASI05 should not be written until normal ClawGuard runtime behavior has a clear "do not alert on this" contract. This document defines the clean behavior that future detectors must preserve.

The rule for detector promotion is:

```text
Normal cron/search/deploy events are evidence, not findings.
```

## Current Project Implements

- Runtime events under schema `runtime-events/0.1`.
- Host-side runtime-event redaction before export.
- A curated clean runtime-event baseline:

```text
lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/runtime_events.json
```

- Local runtime-event validation:

```powershell
python -B scripts\validate_runtime_events.py --input lessons\runtime-events\2026-05\digest-20260507T041020-50c7d030\runtime_events.json --require asi03
```

- A local clean false-positive fixture for normal ops:

```text
examples/runtime_events_normal_ops.json
```

Validation:

```powershell
python -B scripts\validate_runtime_events.py --input examples\runtime_events_normal_ops.json --require asi03 --require asi05
```

## Recommended (Not Implemented Here)

- A learned anomaly detector over runtime event sequences.
- LLM-as-judge review for ambiguous event chains.
- Blocking/enforcement for runtime events.
- Automated promotion from runtime event to finding without a deterministic rule and reviewer-facing evidence.

## ASI03 Normal Behavior That Must Stay Clean

| Runtime fact | Normal example | Future detector expectation |
|---|---|---|
| `identity_context` | `openclaw-job-search` using a label-only profile target | Do not alert. This anchors the session identity. |
| `credential_use` | `brave-search-provider-credential` or `usajobs-search-provider-credential` | Do not alert when the target is a known provider credential label and no raw credential material is present. |
| `network_egress` | `api.search.brave.com` or `data.usajobs.gov` | Do not alert when the egress target is an approved provider domain and policy is `allow`. |
| `file_write` | `digest-output` or `runtime-events` path labels | Do not alert when the artifact is expected and path data is label-only. |
| `policy.decision` | `allow` or `observe` with baseline reason | Do not alert by itself. Policy metadata explains behavior; it is not suspicious without a rule-specific trigger. |

ASI03 should move to `review` only when at least one of these is true:

- A credential label is outside the approved provider/deploy inventory.
- Credential use is followed by egress to a non-approved destination.
- An identity context switch appears without an approved workflow reason.
- Runtime evidence includes a file access event for a secret label outside the approved profile/config path labels.
- Validator-safe evidence still indicates attempted credential movement, such as a redacted credential hash flowing to an external destination.

ASI03 must never persist raw credentials, raw profile paths, raw tokens, or private host identifiers.

## ASI05 Normal Behavior That Must Stay Clean

| Runtime fact | Normal example | Future detector expectation |
|---|---|---|
| `process_exec` | `python unittest discover`, evaluator scripts, validator scripts | Do not alert for approved local validation labels. |
| `container_action` | deploy helper py-compile/import check against the OpenClaw runtime container label | Do not alert for approved deploy-helper labels. |
| `file_write` | telemetry, digest, runtime-event, and curated lesson artifact writes | Do not alert when path labels are approved and raw paths are not stored. |
| `policy.decision` | `allow` for expected cron/deploy, `review` for manual deploy helper operations | Do not alert by itself. Use it as context. |
| `operation_category` | `process-exec`, `container-exec`, `file-write` | Do not alert on category alone; match operation, actor, target, and policy together. |

ASI05 should move to `review` only when at least one of these is true:

- A process label is outside the approved command inventory.
- A command/action label is derived from job content, application text, or other untrusted input.
- A container action changes runtime state outside deploy/cron workflow labels.
- A cron or deployment file mutation appears outside the approved deploy helper.
- A file write targets an unapproved path label or records raw path data.

ASI05 must never persist raw command lines, raw arguments, private filesystem paths, container identifiers, host identifiers, or secrets.

## Approved Baseline Inventory

This inventory is intentionally small. Future detector code should reference this as a starting point, not as an unlimited allowlist.

### Identity and Credentials

- `actor.id`: `openclaw-job-search`
- Credential labels:
  - `brave-search-provider-credential`
  - `usajobs-search-provider-credential`
- Service/profile labels:
  - `openclaw-job-search-profile`
  - `openclaw-maintenance-profile`

### Network Targets

- `api.search.brave.com`
- `data.usajobs.gov`

### File Path Labels

- `digest-output`
- `runtime-events`
- `clawguard-telemetry-latest`
- `application-materials` only when an auto-prepare flow actually writes materials

### Process and Container Labels

- `python unittest discover`
- `evaluate asi06 fixture`
- `evaluate asi02 fixture`
- `evaluate combined detector fixture`
- `validate telemetry sample`
- `validate runtime events`
- `deploy helper py-compile`
- `deploy helper import check`
- `cron wrapper search run`
- `cron wrapper compile run`

## Detector Promotion Requirements

Before ASI03 or ASI05 code is added:

1. Add a local clean fixture that covers the approved baseline inventory.
2. Add detector tests proving the baseline fixture produces zero findings.
3. Add positive synthetic fixtures scoped to local runtime events only.
4. Keep live provider data clean; do not seed synthetic malicious jobs into live providers.
5. Validate all curated runtime-event artifacts before using them as review evidence.

## Next Implementation Slice

1. Add a local `examples/runtime_events_normal_ops.json` fixture that models the approved baseline inventory. Done.
2. Add a validator test proving the fixture satisfies `--require asi03 --require asi05`. Done.
3. Use the fixture as the clean false-positive set when ASI03/ASI05 detector skeletons are written.
4. Defer detector implementation until the clean false-positive set and positive local-only fixtures both exist.
