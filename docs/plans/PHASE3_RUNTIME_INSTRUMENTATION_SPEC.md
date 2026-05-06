# Phase 3 - Runtime Event Instrumentation Spec

Last updated: 2026-05-06
Status: Implementation spec; runtime writer module not yet built
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

## Implementation Decisions

These decisions close architectural questions that would otherwise force the
Day 1 implementer to make ad hoc choices.

### Code Location

Add the writer at:

```text
target-agent/skills/job-search-custom/runtime_events.py
```

It lives alongside `job_search_secure.py` because `run_daily_digest()` and
`run_jd_security_detections()` are the primary callers. The module imports
nothing from `detections/` so detector tests stay independent.

### Threading Model: Module-Level Singleton

The writer state is a module-level singleton, mirroring how
`ASI06_DETECTOR_MODE_LOGGED` already works in `job_search_secure.py`. The
sequence is:

1. `run_daily_digest()` calls `start_runtime_event_session(agent_session_id)`
   exactly once per session. This sets the module-level `_session` global and
   emits the first `identity_context` event.
2. Downstream functions (`score_job`, `_search_brave_site`,
   `_search_usajobs_api`, `prepare_application`, persistence helpers) call
   `record_runtime_event(event)` directly without passing a writer reference.
3. `run_daily_digest()` calls `flush_runtime_events()` exactly once at the end
   of the session, after the digest is built and before
   `clawguard_post_compile.sh` runs.

Rationale: passing a writer reference through every signature would require
editing every detector adapter and provider helper. The singleton pattern is
already in use for the detector activation flags, so it stays consistent. Tests
reset the singleton between cases using a fixture helper.

If concurrency is added later (it is not in scope today), upgrade to a
`contextvars.ContextVar` keyed on `agent_session_id`.

### Recursion Avoidance for `file_write` Self-Emission

The writer itself writes a JSON file under `/data/clawguard/runtime_events/`.
Naively emitting a `file_write` event for that write creates infinite
recursion. The rule is:

```text
record_runtime_event() must never be called from inside the writer's own
file output path.
```

Concretely:

- `flush_runtime_events()` does the disk write; it is **not** wrapped with
  `record_runtime_event("file_write", ...)`.
- Other file writes (digest output, telemetry, application materials) **are**
  wrapped, because their callers are upstream of the writer.
- A single self-describing event is emitted at session close instead:
  `runtime_event_write` with category `runtime-events-self`. This is recorded
  before the actual disk write, so it appears in the same JSON document it
  describes.

### Flush Timing: End-of-Session Only

For Phase 3 observe-only mode, each session emits at most ~10-20 events. Flush
exactly once at session end:

- One disk write per session.
- One atomic rename: write to PID-scoped tempfile under the same directory,
  then `os.replace()` onto the target path. This matches how
  `clawguard_post_compile.sh` writes `telemetry_latest.json`.
- If the process crashes mid-session, no runtime-event file is written. This
  is acceptable because the post-compile telemetry is the system of record;
  runtime events are auxiliary observability.

If review later needs partial data on crash, upgrade to periodic flush
explicitly with a documented interval.

### Env Gate

```text
CLAWGUARD_RUNTIME_EVENTS_ENABLED=1
```

Default off. The writer is a no-op when unset, matching the existing
"silent-by-default" posture for detector activation logs. The
`staggered_cron.sh` wrapper must forward this variable into the container,
the same way it now forwards `CLAWGUARD_EMAIL_TO`.

## Implementation Plan

### Step 1 - Local Writer

Add a writer module at `target-agent/skills/job-search-custom/runtime_events.py`
implementing:

```text
start_runtime_event_session(agent_session_id)
record_runtime_event(event_type, **fields)
flush_runtime_events()
reset_for_tests()
```

Keep it disabled by default until tests cover it. Env flag:

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
- Round-trip: a writer-emitted file passes
  `scripts/validate_runtime_events.py --require asi03 --require asi05`. This
  is the proof that the writer and the validator agree on shape.
- `flush_runtime_events()` does not recurse into `record_runtime_event()`.
- Singleton resets cleanly between sessions in `reset_for_tests()`.

### Step 3 - Preflight

Extend `scripts/preflight.ps1` only after local tests pass:

```powershell
python -B scripts\validate_runtime_events.py --input examples\runtime_events_minimal.json --require asi03 --require asi05
```

This command already exists. Add new generated-fixture validation when the runtime writer exists.

### Step 4 - Deploy Observe-Only

The deploy script must ship the new writer module. Extend
`scripts/deploy_openclaw_skill.ps1` so:

1. `runtime_events.py` is copied into the skill directory next to
   `job_search_secure.py`.
2. `py_compile` covers `runtime_events.py` after the detectors.
3. The cron wrapper forwards `CLAWGUARD_RUNTIME_EVENTS_ENABLED` into the
   container alongside `CLAWGUARD_EMAIL_TO`.
4. The deploy includes an idempotent `mkdir -p
   /data/clawguard/runtime_events` inside the container so the writer's first
   call does not race the directory.

This mirrors the lesson from the post-compile-hook deploy gap: anything the
runtime expects on disk must be produced by the deploy helper, not assumed
to exist.

Deploy with runtime events enabled only after:

- Email/daily schedule is healthy.
- Telemetry schema `1.2` is confirmed.
- Dry-run deploy shows runtime, detections, post-compile hook, cron wrapper,
  and the new `runtime_events.py`.
- `cron_runtime_events_forwarding=ok` assertion passes (modeled on
  `cron_email_to_forwarding=ok`).

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
