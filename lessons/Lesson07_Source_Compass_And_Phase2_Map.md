# 🎓 Lesson 07: The Source Compass - Digest Semantics + Phase 2 Map

## 🛡️ Welcome Back, Operations Engineer

Goal: understand the four-state source-status semantics added in Phase 1 close, why they matter for operations, and where Phase 2 takes the project next.

Time estimate: 30 minutes

Prerequisites:

- Complete Lessons 00-06.
- Understand the daily digest flow from Lesson 01.
- Know how `agent_session_id` correlates findings across rules from Lesson 03.

Why this matters: before Phase 1 close, "the source returned 10 already-known jobs" looked identical to "the source returned nothing" in logs. Operators couldn't tell whether a quiet day meant the pipeline was healthy or broken. This lesson covers the fix and the Phase 2 plans that follow.

## 1. Introduction Section

### Learning objectives

- Explain the four source-status states: `OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR`.
- Inspect a `SEARCH_COMPLETED` audit event and identify its source-status field.
- Read a digest summary and distinguish `total_found`, `new_jobs`, and `newly_inserted_in_run`.
- Locate the Phase 2 plan documents and explain their scope.
- Identify what is implemented in Phase 1 vs. recommended for Phase 2.

### Plain-English explanation

Phase 1 added a "compass" to source searches: every search outcome reports which of four states it landed in. That makes operational debugging deterministic instead of inferential. Phase 2 plans extend the detection engine (ASI02) and formalize the telemetry export workflow.

Analogy: the source-status field is like the dashboard light on a car. Before, you only knew the engine wasn't roaring — could be idling, could be broken, could be parked. Now four lights tell you exactly which.

### Project implements

- Source-status logic: [job_search_secure.py:1404-1437](../target-agent/skills/job-search-custom/job_search_secure.py)
- Digest summary fields: `newly_inserted_in_run`, `compile_only` (line ~2253)
- Compile-mode log clarity: lines ~2143-2154
- Test: `test_search_site_emits_source_status_audit_event` in [test_job_search_secure.py](../tests/test_job_search_secure.py)
- Phase 2 umbrella spec: [docs/plans/PHASE2_SPEC.md](../docs/plans/PHASE2_SPEC.md)
- Phase 2 index: [docs/plans/PHASE2_INDEX.md](../docs/plans/PHASE2_INDEX.md)
- ASI02 spec: [docs/plans/PHASE2_ASI02_SPEC.md](../docs/plans/PHASE2_ASI02_SPEC.md)
- Telemetry workflow plan: [docs/plans/PHASE2_TELEMETRY_WORKFLOW.md](../docs/plans/PHASE2_TELEMETRY_WORKFLOW.md)

### Recommended (not implemented here)

- Schema migration: persist `source_status` and `already_known_count` as columns on `search_runs` (Phase 1 added them to the audit log JSON only).
- Per-source SLO dashboards: alert when a source moves from `OK_NEW` to `ALL_KNOWN` for more than N consecutive days.
- Cross-source correlation: detect coordinated `EMPTY` from multiple providers (possible upstream issue).
- Tool-call telemetry instrumentation needed for Phase 3 ASI02 Layer 3/4.

## 2. Key Concepts Section

### The four source-status states

| State | Meaning | Triggered when |
|---|---|---|
| `OK_NEW` | Source healthy, new candidates found | `len(jobs) > 0 AND new_count > 0` |
| `ALL_KNOWN` | Source healthy, returned only known candidates | `len(jobs) > 0 AND new_count == 0` |
| `EMPTY` | Source returned no candidates | `len(jobs) == 0` |
| `ERROR` | All providers failed for this source | All providers raised exceptions in the fallback chain |

The state is recorded in two places:

1. **Audit log JSON** — `audit_log("SEARCH_COMPLETED", source_status=..., new=..., already_known=..., ...)` writes a structured event to `job_search_audit.log`.
2. **Human-readable INFO log** — `Found 10 jobs on LinkedIn via brave [ALL_KNOWN: 10 already-known candidates]`.

### Why the audit log carries the truth, not the DB

Project implements:

- The audit log JSON is the canonical record of source status.
- The DB `search_runs` table is unchanged — `error TEXT` still distinguishes the failure path; the other three states have to be inferred from `jobs_found` and `new_jobs` columns.

Recommended (not implemented here):

- Migrate `search_runs` to add a `source_status` column. This is intentionally deferred to Phase 2 because the live VPS schema would need migration and Phase 1's goal was clarity, not data-model change.

The "log first, schema later" pattern is common when telemetry needs to catch up to operational reality. Capture the signal where it is cheap (logs), then invest in schema once the signal is proven valuable.

### Digest summary changes

File: [job_search_secure.py](../target-agent/skills/job-search-custom/job_search_secure.py) digest construction

Before Phase 1 close, the digest summary's `new_jobs` field had dual semantics:

- In search mode: newly inserted jobs from this run.
- In compile-only mode: all jobs evaluated from the DB.

That made the field misleading when readers assumed one meaning. Phase 1 added two unambiguous fields:

```python
"summary": {
    "total_found": len(all_jobs),
    "new_jobs": new_jobs_total if not compile_only else len(all_jobs),  # legacy
    "newly_inserted_in_run": new_jobs_total,                            # new, unambiguous
    "compile_only": compile_only,                                        # new, mode flag
    ...
}
```

Why both old and new: keeping `new_jobs` preserves backwards-compatibility for downstream telemetry consumers; `newly_inserted_in_run` and `compile_only` give new readers an unambiguous source of truth.

## 3. Code Walkthrough Section

### Source-status assignment

File: [job_search_secure.py:1411-1429](../target-agent/skills/job-search-custom/job_search_secure.py)

```python
new_count = _persist_search_results(db, run_id, site_key, query, location, jobs, credits)
already_known = max(0, len(jobs) - new_count)
if not jobs:
    source_status = "EMPTY"
    status_note = "no candidates returned"
elif new_count == 0:
    source_status = "ALL_KNOWN"
    status_note = f"{already_known} already-known candidates"
else:
    source_status = "OK_NEW"
    status_note = f"{new_count} new, {already_known} already known"
audit_log("SEARCH_COMPLETED", method=method, site=site_key, results=len(jobs),
          new=new_count, already_known=already_known,
          source_status=source_status, cost=credits)
logger.info(
    f"Found {len(jobs)} jobs on {config['name']} via {method} "
    f"[{source_status}: {status_note}]"
)
```

Line-by-line:

1. `_persist_search_results` returns the count of newly inserted (new-to-DB) jobs after dedup.
2. `already_known = max(0, len(jobs) - new_count)` — clamped to zero in case dedup logic ever returns more than the input length (defensive).
3. The if/elif/else picks one of three statuses; the failure path (line 1437) handles `ERROR` separately.
4. The audit log carries all three counts (`results`, `new`, `already_known`) plus the status string for queryability.
5. The INFO log includes the status in brackets so operators reading the cron log can immediately tell which state hit.

### Failure path

File: [job_search_secure.py:1432-1441](../target-agent/skills/job-search-custom/job_search_secure.py)

```python
error = " | ".join(provider_errors)
final_status = "ERROR" if any(":" in pe and "returned 0 jobs" not in pe for pe in provider_errors) else "EMPTY"
audit_log("SEARCH_FAILED", site=site_key, error=error, source_status=final_status)
if db:
    db.record_search_run(run_id, site_key, query, location, 0, 0, 0, error)
return [], 0
```

Why the conditional: the fallback chain may have logged "returned 0 jobs" without an exception. That's `EMPTY`, not `ERROR`. Real provider exceptions (HTTP errors, parsing failures) carry `:` and a non-zero-jobs message. The discriminator keeps `ERROR` reserved for actual failures rather than diluting it with empty-source noise.

### Compile-mode log clarity

File: [job_search_secure.py:2143-2154](../target-agent/skills/job-search-custom/job_search_secure.py)

```python
if compile_only:
    logger.info(
        f"Compiling digest ({mode_label}): {len(today_jobs_data)} jobs to evaluate "
        f"(compile-only; sources not searched this run)"
    )
else:
    logger.info(
        f"Compiling digest ({mode_label}): {len(today_jobs_data)} jobs to evaluate, "
        f"{new_jobs_total} newly inserted from this run"
    )
```

Why this matters: cron logs are the first place operators look. Before, the line said "Compiling digest: 22 jobs" — readers couldn't tell if those were new today or old in the DB. The new line states both numbers and the mode.

## 4. Hands-On Exercises Section

### 🧪 Exercise 1: Inspect today's audit log entries on the VPS

Bash (read-only SSH):

```bash
ssh -o BatchMode=yes root@31.97.139.139 'tail -20 /docker/openclaw-utxu/data/clawguard/logs/cron.log | grep -E "Found|SEARCH_COMPLETED" || echo "no recent search lines yet"'
```

Expected output (varies by day):

```text
2026-05-04 16:30:03,XXX [INFO] Found 5 jobs on LinkedIn via brave [ALL_KNOWN: 5 already-known candidates]
```

Why: this is how an operator confirms today's source state from the VPS without diving into the database.

### 🧪 Exercise 2: Read the source-status assignment unit test

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest tests.test_job_search_secure.JobSearchSecureTests.test_search_site_emits_source_status_audit_event -v
```

Expected output:

```text
test_search_site_emits_source_status_audit_event ... ok
```

Why: the test stubs the source providers and persistence layer to drive `search_site` through `OK_NEW` and `ALL_KNOWN` paths in the same run. It is the regression boundary that protects the four-state contract.

### 🧪 Exercise 3: Inspect the Phase 2 plan documents

Bash:

```bash
cd /c/Projects/ClawGuard
ls docs/plans/
```

Expected output:

```text
PHASE2_ASI02_SPEC.md
PHASE2_INDEX.md
PHASE2_SPEC.md
PHASE2_TELEMETRY_WORKFLOW.md
```

Then read the index:

```bash
cat docs/plans/PHASE2_INDEX.md | head -30
```

Why: Phase 2 is a doc-first phase. Reading the plans before any code is written is the contract that prevents Phase 2 from drifting into reactive coding.

### 🧪 Exercise 4: Manually trigger each source-status state

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c @"
from unittest.mock import patch
import importlib.util, sys
from pathlib import Path
script = Path('target-agent/skills/job-search-custom/job_search_secure.py')
spec = importlib.util.spec_from_file_location('job_search_secure', script)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
sample = m.Job(job_id='ss', title='SOC', company='Acme', location='Remote',
               description='SIEM', url='https://www.linkedin.com/jobs/view/ss',
               source='linkedin')
events = []
m.audit_log = lambda evt, **d: events.append((evt, d))
m._provider_order = lambda *a, **k: ['brave']
# OK_NEW
m._search_brave_site = lambda *a, **k: ([sample], 0)
m._persist_search_results = lambda *a, **k: 1
m.search_site('linkedin', 'soc', 'Remote')
# ALL_KNOWN
m._persist_search_results = lambda *a, **k: 0
m.search_site('linkedin', 'soc', 'Remote')
# EMPTY
m._search_brave_site = lambda *a, **k: ([], 0)
m.search_site('linkedin', 'soc', 'Remote')
for evt, d in events:
    if 'source_status' in d:
        print(evt, d.get('source_status'))
"@
```

Expected output:

```text
SEARCH_COMPLETED OK_NEW
SEARCH_COMPLETED ALL_KNOWN
SEARCH_EMPTY_FALLBACK EMPTY
```

Why: this confirms the state machine behaves correctly without needing live providers.

## 5. Interview Preparation Section

**Q: Why didn't you migrate `search_runs` to add a `source_status` column instead of putting it in the audit log?**

**A:** Schema migration on a live VPS is heavier weight than the Phase 1 goal justified. The audit log captures the signal immediately and lets the value of the data be proven before paying the migration cost. Phase 2's telemetry workflow plan covers the eventual schema migration. This is the "log first, schema later" pattern — common when telemetry needs to catch up to operational reality.

**Q: How does an operator distinguish a quiet but healthy pipeline from a broken one?**

**A:** The four source-status states. `ALL_KNOWN` for many consecutive days is a healthy quiet signal — sources are working, content just hasn't changed. `EMPTY` for many consecutive days suggests sources are misconfigured or geofenced. `ERROR` indicates real provider failures. Coordinated state changes across multiple providers — say, all flipping to `EMPTY` simultaneously — point to upstream issues like API key expiry or network changes.

**Q: What's the relationship between `new_jobs` and `newly_inserted_in_run` in the digest summary?**

**A:** `new_jobs` has dual semantics for backwards compatibility — it equals `newly_inserted_in_run` in search mode but `total_found` in compile-only mode. `newly_inserted_in_run` is the unambiguous field added in Phase 1 close. `compile_only` is the mode flag so consumers can tell which interpretation `new_jobs` carries. New consumers should read `newly_inserted_in_run` and `compile_only`; legacy consumers can keep reading `new_jobs`.

**Q: What's the first piece of Phase 2 that should ship?**

**A:** The telemetry export workflow. ASI02 needs realistic samples to evaluate false-positive rates against, and the curated export pipeline produces those samples. Once the workflow lands, ASI02 can be developed against real adversarial content rather than synthetic fixtures alone.

## 6. Key Takeaways Section

- Source searches now report one of four states: `OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR`.
- The audit log JSON is the canonical record; DB schema is unchanged for now.
- Digest summary adds `newly_inserted_in_run` and `compile_only` for unambiguous counts.
- Phase 2 plans live under `docs/plans/` - v3 umbrella spec, ASI02 detection module, curated telemetry workflow, corpus/red-team discipline, and ASI03/ASI05 roadmap specs.
- "Log first, schema later" keeps Phase 1 closure cheap while preserving the option to migrate.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| States | `OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR` |
| Audit event field | `source_status` (in `SEARCH_COMPLETED` and `SEARCH_FAILED`) |
| Audit count fields | `results`, `new`, `already_known` |
| Digest summary additions | `newly_inserted_in_run`, `compile_only` |
| Test | `test_search_site_emits_source_status_audit_event` |
| Phase 2 index | `docs/plans/PHASE2_INDEX.md` |
| Phase 2 docs | `PHASE2_SPEC.md`, `PHASE2_ASI02_SPEC.md`, `PHASE2_TELEMETRY_WORKFLOW.md` |
| Source-status code | `job_search_secure.py:1411-1437` |

## 8. Next Steps

You've reached the end of the Phase 1 lesson curriculum. To go further:

1. Read [docs/plans/PHASE2_SPEC.md](../docs/plans/PHASE2_SPEC.md) and [docs/plans/PHASE2_INDEX.md](../docs/plans/PHASE2_INDEX.md).
2. Pick the Phase 2 doc that aligns with your interest (detection or operations).
3. Build a synthetic ASI02 fixture and the v1 detector class — the spec in `PHASE2_ASI02_SPEC.md` is detailed enough to start from.

Optional advanced topics:

- Add an SLO dashboard that consumes the `source_status` audit field and alerts on consecutive-`EMPTY` runs.
- Migrate `search_runs` to include `source_status` and `already_known_count` columns; write a backfill that parses historical audit-log entries.
- Implement Layer-4 LLM-as-judge for ASI01 ambiguous cases (referenced in [Lesson 06](Lesson06_ASI01_Goal_Hijack_Scaffold.md) interview prep).

Remember: clarity in operations beats cleverness in code. 🛡️
