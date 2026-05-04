# Phase 2 — Curated Telemetry Export Workflow

Last updated: 2026-05-04
Status: Plan; current state is the Phase 1 manual workflow described below
Predecessor: `scripts/export_latest_telemetry.ps1`, post-compile hook

## Context

Phase 1 set up VPS-side telemetry generation:

- `clawguard_post_compile.sh` writes per-session JSON+MD telemetry to `/data/clawguard/telemetry/`.
- `telemetry_latest.{json,md}` is updated atomically after each compile.
- `scripts/export_latest_telemetry.ps1` lets a human pull curated samples to `lessons/telemetry/`.
- The repo intentionally does **not** auto-push from the VPS. The architectural rule is:

```text
VPS telemetry  = continuous operational record
Repo telemetry = curated review artifacts only
Auto-push      = intentionally deferred
```

This works for one human reviewer and a handful of clean-baseline sessions. It will not scale once ASI01 / ASI02 start firing on real adversarial content and the volume of review-worthy artifacts grows.

## Phase 2 Goals

1. **Make selection deterministic.** A reviewer should be able to ask "give me all sessions where ASI01 fired this week" and get an answer without manually reading logs.

2. **Preserve redaction guarantees.** Email addresses are already redacted in `check_cron_confirmation.ps1`. Telemetry export must apply equivalent redaction before any artifact lands in the repo.

3. **Track schema versions.** ASI01 v1 added new evidence fields (`related_asi06_rule_id`, `attempted_goal_categories`). ASI02 will add more. The export pipeline must surface the schema version of each session to keep historical samples interpretable.

4. **Keep the architectural rule intact.** No auto-push from the VPS. Selection happens in the repo, transport is a human-triggered pull.

## Workflow Design (Phase 2)

### Step 1 — Selection on VPS

Add a small helper at `/docker/openclaw-utxu/data/clawguard/select_review_sessions.sh` that scans telemetry JSON and prints sessions matching review criteria:

```bash
select_review_sessions.sh --since YYYY-MM-DD --rule ASI01_EXTERNAL_GOAL_REDIRECT
select_review_sessions.sh --since YYYY-MM-DD --finding-count-min 1
select_review_sessions.sh --baseline   # clean sessions for regression testing
```

Output is a list of `agent_session_id` values. The script reads `telemetry_<date>_<id>.json` files and applies `jq`-style filters in pure shell.

### Step 2 — Curated pull

Extend `scripts/export_latest_telemetry.ps1` with a `--Sessions <list>` flag (or rename to `export_telemetry.ps1` with backwards-compatible default). Given a list of session IDs, it:

1. SCPs the matching JSON+MD files to a local temp directory.
2. Applies redaction (email regex, phone regex, configurable additional patterns).
3. Validates each artifact against the current telemetry schema.
4. Writes redacted artifacts to `lessons/telemetry/<YYYY-MM>/<agent_session_id>/`.
5. Generates a `lessons/telemetry/<YYYY-MM>/index.md` that links each session and shows finding counts.

Important: this remains a *human-triggered pull*. The VPS does not initiate transfer.

### Step 3 — Schema versioning

Add a top-level `schema_version` field to `telemetry_<date>_<id>.json` written by the post-compile hook. Bump on shape changes:

- `1.0` — Phase 1 baseline (ASI06-only).
- `1.1` — ASI01 fields (`related_asi06_rule_id`, `attempted_goal_categories`).
- `1.2` — ASI02 fields (planned).

The `validate_telemetry.py` script gains per-version branches. `lessons/telemetry/<month>/index.md` records the schema version of each session so old samples remain interpretable when the schema evolves.

### Step 4 — Retention & storage budget

Curated repo artifacts are small JSON+MD; storage is a non-issue. The retention policy keeps:

- All months' sessions where any ASI rule fired.
- The first clean baseline of each month (regression reference).
- Manually annotated sessions used in lesson curriculum.

Older clean-baseline sessions can be pruned via a `--prune` flag once they're no longer referenced.

### Step 5 — Documentation

Update `lessons/README.md` with the new selection / export commands. Add a short section to `docs/MONITORING.md` explaining the pull workflow.

## What Does Not Change

- VPS retains full operational telemetry on its own volume.
- `clawguard_post_compile.sh` continues writing per-session and `_latest` files atomically.
- Email and Telegram notifications are not affected.
- No new VPS-side credentials are introduced.

## Tests

- Unit: `tests/test_validate_telemetry.py` (new) — validates each schema version's shape.
- Unit: `tests/test_export_redaction.py` (new) — confirms redaction strips emails, phone numbers, and any configured extras before artifacts hit the repo.
- Integration: a dry-run mode for `export_telemetry.ps1` that prints the planned operations without running scp/ssh.

## Verification

1. Local: `python scripts\validate_telemetry.py --input examples/telemetry_v1.1_sample.json` succeeds.
2. Local: `.\scripts\export_telemetry.ps1 --DryRun --Sessions sample-id` prints planned actions and exits 0.
3. End-to-end: curated pull of yesterday's sessions produces `lessons/telemetry/2026-05/<id>/` with redacted artifacts and an updated `index.md`.

## Migration Steps

1. Add `schema_version` field to post-compile hook (small, backwards-compatible).
2. Land `select_review_sessions.sh` on VPS.
3. Extend the existing PowerShell helper with `--Sessions` and redaction.
4. Add per-version branches to `validate_telemetry.py`.
5. Re-export historical samples to update their structure.
6. Document the new workflow.

Each step is independently shippable. Step 1 is the only VPS-side change and can land first without changing the repo's telemetry export contract.

## Open Questions

1. Does the `select_review_sessions.sh` filter set need a "reviewer needs to look" flag separate from "any ASI rule fired"? Some findings will be informational (low severity, high false-positive risk) and shouldn't always go in the repo.
2. Should redaction be applied on the VPS before transfer, or in the local helper after transfer? Local-side redaction is simpler; VPS-side is safer if the pull command is ever automated.
3. How does this workflow interact with the cron-confirmation script's email-redaction step? They should share a single redaction function rather than duplicating regexes.
