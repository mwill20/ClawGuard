# Phase 2 - Curated Telemetry Export Workflow

Last updated: 2026-05-05
Status: In progress; schema versioning and structured session selection are implemented
Predecessor: `scripts/export_latest_telemetry.ps1`, post-compile hook

## Context

Phase 1 set up operational telemetry generation:

- `clawguard_post_compile.sh` writes per-session JSON+MD telemetry to `/data/clawguard/telemetry/`.
- `telemetry_latest.{json,md}` is updated atomically after each compile.
- `scripts/export_latest_telemetry.ps1` lets a human pull curated samples to `lessons/telemetry/`.
- The repo intentionally does **not** auto-push from the operational host.

The architectural rule is:

```text
Operational telemetry = continuous operational record
Repo telemetry        = curated review artifacts only
Auto-push             = intentionally deferred
```

This works for one human reviewer and a handful of clean-baseline sessions. It will not scale once ASI01 and ASI02 findings generate more review-worthy artifacts.

## Phase 2 Goals

1. **Make selection deterministic.** A reviewer should be able to ask "give me all sessions where ASI01 fired this week" and get an answer without manually reading logs.

2. **Preserve redaction guarantees.** Email addresses are already redacted in cron confirmation. Telemetry export must apply equivalent or stronger redaction before any artifact lands in the repo.

3. **Track schema versions.** ASI01 v1 added new evidence fields. ASI02 will add more. The export pipeline must surface schema version so historical samples remain interpretable.

4. **Keep the architectural rule intact.** No auto-push from the operational host. Selection and transport remain human-triggered.

## Workflow Design

### Step 1 - Structured Selection

`scripts/select_review_sessions.py` scans telemetry JSON and prints sessions matching review criteria. It can run locally against pulled artifacts or on the operational host when manually invoked.

```powershell
python -B scripts\select_review_sessions.py --telemetry-dir C:\tmp\clawguard-telemetry --since 2026-05-01 --rule ASI01_EXTERNAL_GOAL_REDIRECT
python -B scripts\select_review_sessions.py --telemetry-dir C:\tmp\clawguard-telemetry --since 2026-05-01 --finding-count-min 1
python -B scripts\select_review_sessions.py --telemetry-dir C:\tmp\clawguard-telemetry --baseline
```

Output is a newline-delimited list of `agent_session_id` values. The script reads JSON with Python's JSON parser and skips non-telemetry JSON files safely.

### Step 2 - Curated Pull

Extend `scripts/export_latest_telemetry.ps1` with a `--Sessions <list>` flag, or add `scripts/export_telemetry.ps1` with a backwards-compatible default. Given a list of session IDs, it:

1. SCPs the matching JSON+MD files to a local temp directory.
2. Applies redaction.
3. Validates each artifact against the current telemetry schema.
4. Writes redacted artifacts to `lessons/telemetry/<YYYY-MM>/<agent_session_id>/`.
5. Generates `lessons/telemetry/<YYYY-MM>/index.md` with session links and finding counts.

Important: this remains a human-triggered pull. The operational host does not initiate transfer.

### Step 3 - Redaction

Redaction must cover:

- Email addresses.
- Phone numbers.
- Deployment identifiers.
- Private profile strings.
- Configurable additional patterns.

Local-side redaction is the Phase 2 default because it is simpler and testable. Host-side redaction should be reconsidered before any automation.

### Step 4 - Schema Versioning

Telemetry JSON includes a top-level `schema_version` field written by the post-compile hook.

Version plan:

- `1.0` - Phase 1 baseline shape.
- `1.1` - ASI01 evidence fields.
- `1.2` - ASI02 evidence fields.

`scripts/validate_telemetry.py` validates supported schema versions. `lessons/telemetry/<month>/index.md` will record each session's schema version after the export helper is extended.

### Step 5 - Retention

Curated repo artifacts are small JSON+MD. Keep:

- All sessions where any ASI rule fired.
- The first clean baseline of each month.
- Manually annotated sessions used in lesson curriculum.

Older clean-baseline sessions can be pruned via a `--Prune` flag once they are no longer referenced.

## What Does Not Change

- The operational host retains full telemetry on its own volume.
- `clawguard_post_compile.sh` continues writing per-session and `_latest` files atomically.
- Email and Telegram notifications are not affected.
- No new operational-host credentials are introduced.

## Tests

- Unit: `tests/test_telemetry_validation.py` validates schema-version branches.
- Unit: add `tests/test_export_redaction.py` for email, phone, deployment identifier, and configured-extra redaction.
- Unit: `tests/test_select_review_sessions.py` covers selection by rule, count, date, and baseline status.
- Integration: add dry-run mode that prints planned export operations without running scp/ssh.

## Verification

1. Local: `python scripts\validate_telemetry.py --input examples\telemetry_sample.json` succeeds.
2. Local: `python -B scripts\select_review_sessions.py --telemetry-dir examples --finding-count-min 1` prints matching session IDs and exits 0.
3. Local: `.\scripts\export_telemetry.ps1 --DryRun --Sessions sample-id` prints planned actions and exits 0.
4. End-to-end: curated pull of selected sessions produces `lessons/telemetry/2026-05/<id>/` with redacted artifacts and an updated `index.md`.

## Migration Steps

1. Add `schema_version` field to post-compile hook. Done.
2. Add `scripts/select_review_sessions.py`. Done.
3. Extend or replace the existing PowerShell export helper with `--Sessions` and redaction.
4. Add per-version branches to `validate_telemetry.py`. Done.
5. Re-export historical samples to update their structure.
6. Document the new workflow in `lessons/README.md` and `docs/MONITORING.md`.

Each step is independently shippable. Schema versioning is the only runtime-output change and can land first without changing the repo's telemetry export contract.

## Open Questions

1. Does the selector need a "reviewer needs to look" flag separate from "any ASI rule fired"?
2. Should redaction be applied on the operational host before transfer, or in the local helper after transfer?
3. How does this workflow interact with the cron-confirmation script's email-redaction step? They should share a single redaction function rather than duplicating regexes.
