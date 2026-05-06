# 🎓 ClawGuard Lesson Index

Assumptions and scope:

- Phase 1 closed on 2026-05-04 with ASI01 v1 deployed and cron-confirmed.
- Line references in lessons are accurate as of Phase 1 close. Re-check after future code movement.
- Lessons live in the existing lowercase `lessons/` directory.
- VPS commands target the current OpenClaw host `root@31.97.139.139` and container `openclaw-utxu-openclaw-1`.
- ASI06, ASI01, and ASI02 detector modules are required runtime dependencies. Inline fallback paths have been removed.
- Phase 2 plans live under `docs/plans/`, with `PHASE2_SPEC.md` as the v3 umbrella spec.

## Required Curriculum

| Lesson | Title | Component | Status |
|---|---|---|---|
| 00 | [The Control Room - Project Architecture](Lesson00_Project_Architecture.md) | Repo architecture and Phase 1 flow | Required |
| 01 | [The Job-Search Command Center - OpenClaw Runtime](Lesson01_OpenClaw_Runtime.md) | `target-agent/skills/job-search-custom/job_search_secure.py` | Required |
| 02 | [The Security Detective - ASI06 Detector](Lesson02_ASI06_Detector.md) | `detections/asi06_jd_content/detector.py` | Required |
| 03 | [The Evidence Ledger - SQLite Findings](Lesson03_SQLite_Telemetry_Ledger.md) | `JobDatabase` and `job_security_findings` | Required |
| 04 | [The Black Box Recorder - Cron and Telemetry Hook](Lesson04_Cron_And_Post_Compile_Telemetry.md) | `staggered_cron.sh`, `clawguard_post_compile.sh`, helper scripts | Required |
| 05 | [The Proving Ground - Tests and Defense Lab](Lesson05_Testing_And_Defense_Lab.md) | `tests/` plus red-team sample data | Required |
| 06 | [The Investigator - ASI01 Goal Hijack Detector v1](Lesson06_ASI01_Goal_Hijack_Scaffold.md) | `detections/asi01_goal_hijack/detector.py` | Required |
| 07 | [The Source Compass - Digest Semantics + Phase 2 Map](Lesson07_Source_Compass_And_Phase2_Map.md) | `search_site` source-status, `docs/plans/` | Required |
| 08 | [The Tool-Use Gatekeeper - ASI02 Defense Lab](Lesson08_ASI02_Tool_Misuse_Defense_Lab.md) | `detections/asi02_tool_misuse/detector.py`, `examples/asi02_labeled_eval.json` | Required |

## Phase Map

```text
OpenClaw source search (with OK_NEW / ALL_KNOWN / EMPTY / ERROR status)
  -> SQLite job storage
  -> ASI06 detector (content patterns)
  -> ASI01 detector (goal-redirect classification on top of ASI06)
  -> ASI02 detector (tool-misuse operation classification)
  -> score and compile digest
  -> post-compile telemetry export
  -> curated lessons and baselines
  -> Phase 2: curated telemetry workflow + ASI03/ASI05 roadmap specs
```

## Project Implements

- Daily low-volume OpenClaw maintenance searches for LinkedIn, CyberSecJobs, and USAJobs.
- Zero-credit provider posture with Brave Search and native USAJobs API.
- SQLite persistence for jobs, search runs, quota, and `job_security_findings`.
- ASI06 detector module as the required runtime integration.
- ASI01 v1 goal-hijack detector as a corroborated classifier on top of ASI06.
- ASI02 v1 tool-misuse detector for unsafe egress, notification redirects, shell payloads, and file-write redirects.
- Source-status semantics in search audit log (`OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR`) and digest summary fields (`newly_inserted_in_run`, `compile_only`).
- Post-compile telemetry JSON/Markdown artifacts.
- Local regression tests covering parsers, session IDs, ASI06 + ASI01 + ASI02 detector behavior, source-status audit, and DB queryability.
- GitHub Actions CI for unit tests, synthetic ASI06/ASI02 fixture evaluation, and telemetry sample validation.
- Small synthetic labeled ASI06 fixture metrics under `examples/`.
- Telemetry sample JSON validation under `examples/`.
- Phase 2 plan documents under `docs/plans/` covering the v3 baseline, ASI02 module, telemetry workflow, corpus/red-team discipline, and ASI03/ASI05 roadmap specs.

## Recommended (not implemented here)

- Prompt sanitization or quarantine before LLM-based summarization.
- Layer-4 semantic guardrails using deterministic policy or LLM-as-judge for ambiguous goal-redirect cases.
- Signed deployment bundles for `job_search_secure.py` plus `detections/`.
- `search_runs` schema migration to persist `source_status` and `already_known_count` columns (currently audit-log only).
- Tool-call telemetry instrumentation (Phase 3 prerequisite for ASI02 Layer 3/4 detection).

## Hands-On Starting Point

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
........................
----------------------------------------------------------------------
Ran 63 tests in 0.49s

OK
```

Bash:

```bash
cd /c/Projects/ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
........................
----------------------------------------------------------------------
Ran 63 tests in 0.49s

OK
```

## How To Use These Lessons

1. Start with Lesson 00 if you need the whole system picture.
2. Study Lessons 01-05 before discussing ClawGuard in an interview.
3. Use Lesson 05 as your hands-on defense lab.
4. Use Lesson 06 to walk through the implemented ASI01 v1 corroborated-classifier design.
5. Use Lesson 07 to understand source-status semantics and the Phase 2 roadmap.
6. Use Lesson 08 to practice ASI02 tool-misuse detection.
