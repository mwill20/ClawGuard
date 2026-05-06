# Phase 3 - Runtime Event Instrumentation Spec

Last updated: 2026-05-05
Status: Draft implementation spec
Input contract: [PHASE2_RUNTIME_TELEMETRY_CONTRACT.md](PHASE2_RUNTIME_TELEMETRY_CONTRACT.md)

## Purpose

ASI03 and ASI05 require runtime facts. This spec turns the `runtime-events/0.1` fixture contract into deployed observe-only instrumentation.

The rule for Phase 3 is simple:

```text
Emit facts first. Detect later.
```

## Event Storage

Recommended host/container paths:

```text
/data/clawguard/runtime_events/runtime_events_<YYYY-MM-DD>_<agent_session_id>.json
/data/clawguard/runtime_events/runtime_events_latest.json
```

Each file should contain:

```json
{
  "schema_version": "runtime-events/0.1",
  "generated_at": "2026-05-06T16:30:00Z",
  "agent_session_id": "digest-20260506T163000-example",
  "events": []
}
```

JSON array files are preferred over JSONL for Phase 3 because the existing validator expects one JSON document and curated export already works with JSON documents.

## Runtime Hook Points

### 1. Session Start

Emit `identity_context` once per `agent_session_id` inside `run_daily_digest()`.

Evidence:

- Profile path label, not raw path.
- Runtime component label.
- `credential_material_present: false`.

### 2. Provider Requests

Emit `credential_use` and `network_egress` around Brave and USAJobs provider calls.

Evidence:

- Provider label: `brave`, `usajobs`.
- Credential label only, never raw key.
- Destination domain, not full query URL if query text may contain private data.
- Policy decision: `allow`.

### 3. File Writes

Emit `file_write` for digest, telemetry, application material, and runtime-event writes.

Evidence:

- Path label such as `digest-output`, `telemetry-latest`, `application-materials`.
- `atomic_write: true` where applicable.
- Raw path stored: false.

### 4. Host Wrapper Commands

Emit `process_exec` and `container_action` from host-side scripts later in Phase 3.

Initial scripts:

- `target-agent/skills/job-search-custom/staggered_cron.sh`
- `scripts/deploy_openclaw_skill.ps1`

Evidence:

- Command label, not raw command line.
- Container label, not private container identifier in curated exports.
- Exit code.
- Policy decision: `allow` for expected cron/deploy operations, `review` for manual deploy.

## Redaction Requirements

Never store:

- Raw API keys.
- Email app passwords.
- Full private profile paths.
- Raw command lines with secrets.
- Raw host identifiers in curated artifacts.
- Raw resume/profile contents.

Allowed:

- Stable labels.
- Redacted hashes.
- Event IDs.
- `agent_session_id`.
- Public provider domains.

## Implementation Plan

### Step 1 - Local Writer

Add a small writer abstraction with:

```text
start_runtime_event_session(agent_session_id)
record_runtime_event(event)
flush_runtime_events()
```

Keep it disabled by default until tests cover it. Suggested env flag:

```text
CLAWGUARD_RUNTIME_EVENTS_ENABLED=1
```

### Step 2 - Tests

Add tests that verify:

- Session event validates.
- Provider event validates.
- Raw secret-shaped fields are rejected.
- Runtime-event files correlate with `agent_session_id`.
- Emission disabled means no file write.

### Step 3 - Preflight

Extend `scripts/preflight.ps1` only after local tests pass:

```powershell
python -B scripts\validate_runtime_events.py --input examples\runtime_events_minimal.json --require asi03 --require asi05
```

This command already exists. Add new generated-fixture validation when the runtime writer exists.

### Step 4 - Deploy Observe-Only

Deploy with runtime events enabled only after:

- Email/daily schedule is healthy.
- Telemetry schema `1.2` is confirmed.
- Dry-run deploy shows runtime, detections, post-compile hook, and cron wrapper.

### Step 5 - Curate Baselines

Export a clean runtime-event baseline first. Then wait for real review-worthy events before building ASI03/ASI05 detectors.

## ASI03 Readiness

ASI03 can move forward when runtime events include:

- `identity_context`
- `credential_use`
- `network_egress` or `file_access`
- policy decisions
- session correlation

Do not implement ASI03 before those exist in real telemetry.

## ASI05 Readiness

ASI05 can move forward when runtime events include:

- `process_exec`
- `container_action` or `file_write`
- policy decisions
- session correlation
- redacted command/target labels

Do not implement ASI05 before those exist in real telemetry.

## Failure Modes

| Failure | Expected Response |
|---|---|
| Runtime events contain raw secret-shaped keys | Validator fails; do not export |
| Runtime events missing session ID | Validator fails; fix writer |
| Daily email fails | Pause Phase 3 deploy; fix ops first |
| Telemetry schema falls back to 1.0 | Redeploy hook; do not curate ASI02/Phase 3 artifacts |
| Provider returns 0 new jobs | Keep ASI02 activation as future evidence trigger |
