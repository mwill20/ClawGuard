# 🎓 ClawGuard Lesson Index

Assumptions and scope:

- Line references are current for the Phase 1 lesson pass and should be rechecked after code movement.
- Lessons live in the existing lowercase `lessons/` directory.
- VPS commands target the current OpenClaw host `root@31.97.139.139` and container `openclaw-utxu-openclaw-1`.
- The inline ASI06 fallback is still intentionally retained until one normal daily cron run confirms the detector-backed path.

## Required Curriculum

| Lesson | Title | Component | Status |
|---|---|---|---|
| 00 | [The Control Room - Project Architecture](Lesson00_Project_Architecture.md) | Repo architecture and Phase 1 flow | Required |
| 01 | [The Job-Search Command Center - OpenClaw Runtime](Lesson01_OpenClaw_Runtime.md) | `target-agent/skills/job-search-custom/job_search_secure.py` | Required |
| 02 | [The Security Detective - ASI06 Detector](Lesson02_ASI06_Detector.md) | `detections/asi06_jd_content/detector.py` | Required |
| 03 | [The Evidence Ledger - SQLite Findings](Lesson03_SQLite_Telemetry_Ledger.md) | `JobDatabase` and `job_security_findings` | Required |
| 04 | [The Black Box Recorder - Cron and Telemetry Hook](Lesson04_Cron_And_Post_Compile_Telemetry.md) | `staggered_cron.sh`, `clawguard_post_compile.sh`, helper scripts | Required |
| 05 | [The Proving Ground - Tests and Defense Lab](Lesson05_Testing_And_Defense_Lab.md) | `tests/` plus red-team sample data | Required |
| 06 | [The Next Detector - ASI01 Scaffold](Lesson06_ASI01_Goal_Hijack_Scaffold.md) | `detections/asi01_goal_hijack/ASI01-001.md` | Optional until ASI06 fallback removal |

## Phase Map

```text
OpenClaw source search
  -> SQLite job storage
  -> ASI06 detector-backed job-content checks
  -> score and compile digest
  -> post-compile telemetry export
  -> curated lessons and baselines
  -> future ASI01/ASI02 detectors
```

## Project Implements

- Daily low-volume OpenClaw maintenance searches for LinkedIn, CyberSecJobs, and USAJobs.
- Zero-credit provider posture with Brave Search and native USAJobs API.
- SQLite persistence for jobs, search runs, quota, and `job_security_findings`.
- ASI06 detector module with runtime integration and inline fallback.
- Post-compile telemetry JSON/Markdown artifacts.
- Local regression tests for parser behavior, session IDs, detector behavior, and DB queryability.
- GitHub Actions CI for unit tests, the synthetic ASI06 fixture evaluation, and telemetry sample validation.
- Small synthetic labeled ASI06 fixture metrics under `examples/`.
- Telemetry sample JSON validation under `examples/`.

## Recommended (not implemented here)

- Schema validation for every telemetry artifact before writing to disk.
- Prompt sanitization or quarantine before LLM-based summarization.
- Semantic guardrails using deterministic classifiers or LLM-as-judge for ASI01 behavior.
- Signed deployment bundles for `job_search_secure.py` plus `detections/`.
- GitHub Actions CI already runs unit tests, the synthetic ASI06 fixture evaluation, and telemetry sample validation. Recommended future expansion: run the full lesson command set and validate exported VPS telemetry artifacts.

## Hands-On Starting Point

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.077s

OK
```

Bash:

```bash
cd /c/Projects/ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.077s

OK
```

## How To Use These Lessons

1. Start with Lesson 00 if you need the whole system picture.
2. Study Lessons 01-05 before discussing ClawGuard in an interview.
3. Use Lesson 05 as your hands-on defense lab.
4. Use Lesson 06 when you are ready to explain the ASI01 roadmap without claiming it is implemented.
