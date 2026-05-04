# 🎓 Lesson 00: The Control Room - Project Architecture

## 🛡️ Welcome Back, AI Security Engineer

Goal: understand why ClawGuard exists, what is implemented today, and how OpenClaw generates real telemetry for detector work.

Time estimate: 25 minutes

Prerequisites:

- You can run PowerShell from `C:\Projects\ClawGuard`.
- You understand basic Python, SQLite, and cron concepts.
- You have read `README.md` once.

Why this matters: ClawGuard is not just a detector library. It is an operational loop around a real OpenClaw deployment, so the architecture has to preserve evidence, avoid noisy automation, and keep future detector work tied to real runs.

## 1. Introduction Section

### Learning objectives

- Explain the Phase 1 OpenClaw-to-ClawGuard pipeline.
- Identify the files that produce runtime behavior, telemetry, and lessons.
- Distinguish implemented detector behavior from future guardrail plans.
- Trace how a job posting becomes a scored job and optional security finding.
- Describe why zero findings are still useful telemetry.
- Explain why the inline ASI06 fallback still exists.

### Plain-English explanation

ClawGuard watches a real job-search agent and asks: "Did untrusted job content try to manipulate the agent?" Today, the system focuses on ASI06 job-description content risks while preserving enough telemetry to build ASI01 and ASI02 later.

Real-world analogy: ClawGuard is the control room for a security camera system. OpenClaw is the camera pointed at real activity. The detector decides what looks suspicious. The telemetry hook stores the footage summary so you can review it later.

### Why it matters

Without this architecture, the project would be a set of disconnected scripts. With it, every detector has a live data source, a database table, a session ID, a digest, and a lesson artifact that can be explained in interviews.

### Project implements

- `README.md` lines 7-24 describe the current Phase 1 posture and daily schedule.
- `README.md` lines 36-42 map ASI01, ASI02, and ASI06 states.
- `PHASE1_PROGRESS.md` lines 18-23 track operational status and schema posture.

### Recommended (not implemented here)

- A formal architecture decision record directory.
- A generated dependency graph for Python imports and shell deployment paths.
- Continuous deployment packaging for `job_search_secure.py` and `detections/`.

## 2. Key Concepts Section

### Domain terms

| Term | Meaning in this project |
|---|---|
| OpenClaw | The running agent target that searches jobs and produces telemetry. |
| ClawGuard | The guardrail and detection layer built around OpenClaw behavior. |
| ASI06 | OWASP Agentic risk category used here for malicious job-description content ingestion. |
| ASI01 | Goal hijacking and instruction override; scaffolded, not runtime implemented. |
| `agent_session_id` | Correlation ID like `digest-20260503T163003-b91b67e1`. |
| Clean baseline | A run with zero findings that proves the pipeline can run without noise. |
| Inline fallback | Old ASI06 code kept inside `job_search_secure.py` until the detector-backed VPS path is confirmed by cron. |

### Larger architecture

```text
Job source APIs
  -> job_search_secure.py
  -> SQLite jobs.db
  -> detections/asi06_jd_content/detector.py
  -> job_security_findings
  -> digest_YYYY-MM-DD.json
  -> clawguard_post_compile.sh
  -> telemetry_latest.json and telemetry_latest.md
  -> lessons/
```

### Design decisions

Project implements:

- Low-volume daily runs so OpenClaw acts as telemetry generator, not application machine.
- Detector-backed ASI06 path with inline fallback for manual VPS deploy safety.
- Manual telemetry export instead of auto-pushing from the VPS.

Recommended (not implemented here):

- Schema/policy checks for every digest and telemetry artifact.
- Prompt sanitization/quarantine before any future LLM semantic analysis.
- Semantic guardrails for ASI01 using deterministic rules or LLM-as-judge.

## 3. Code Walkthrough Section

### Main architecture files

```text
README.md
PHASE1_PROGRESS.md
target-agent/skills/job-search-custom/job_search_secure.py
detections/asi06_jd_content/detector.py
target-agent/skills/job-search-custom/clawguard_post_compile.sh
tests/test_job_search_secure.py
tests/test_asi06_detector.py
```

### Walkthrough: current flow in `README.md`

Inspect:

```powershell
Set-Location C:\Projects\ClawGuard
Get-Content README.md | Select-Object -First 110
```

Key block:

```text
OpenClaw cron
  -> job-search-custom searches LinkedIn, CyberSecJobs, USAJobs
  -> SQLite stores jobs, scores, and ASI06 findings
  -> digest compile creates agent_session_id
  -> clawguard_post_compile.sh exports telemetry JSON/Markdown
  -> lessons/ captures curated baselines and review artifacts
```

What this does:

1. `OpenClaw cron` schedules the work instead of requiring manual runs.
2. `job-search-custom` collects source data.
3. SQLite preserves state across runs.
4. `agent_session_id` creates a join key between digest and findings.
5. `clawguard_post_compile.sh` turns raw DB state into reviewable telemetry.
6. `lessons/` keeps curated learning artifacts separate from continuous VPS telemetry.

Why it is designed this way: real detection work needs repeatable inputs and evidence. The digest plus findings table gives you both.

### Common pitfalls

| Pitfall | Avoid it by |
|---|---|
| Treating 0 findings as failure | Reading clean baselines as noise-control evidence. |
| Claiming ASI01 runtime exists | Saying ASI01 is scaffolded and semantic-first, not implemented. |
| Removing inline fallback too early | Waiting for one normal cron run through the detector-backed path. |

## 4. Hands-On Exercises Section

### 🧪 Exercise 1: Print the project posture

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Get-Content README.md | Select-Object -First 24
```

Expected output begins:

```text
# ClawGuard

Guardrail-first AI agent security monitoring framework.

ClawGuard detects OWASP Agentic Top 10 risks against AI agents by watching a real OpenClaw deployment, not simulated traces.
```

### 🧪 Exercise 2: Confirm the codebase is testable

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.077s

OK
```

### 🧪 Exercise 3: Identify the latest committed phase

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
git log --oneline -5
```

Expected output begins:

```text
11d0189 Log ASI06 detector runtime mode
5a9405a Wire OpenClaw to ASI06 detector
95025fb Implement ASI06 detector module
```

### 🧪 Exercise 4: Intentional failure check

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c "import importlib; importlib.import_module('detections.missing_detector')"
```

Expected output includes:

```text
ModuleNotFoundError: No module named 'detections.missing_detector'
```

Why this matters: the ASI06 runtime catches missing `detections` package imports and falls back, but unrelated missing imports should fail loudly.

## 5. Interview Preparation Section

**Q: What problem does ClawGuard solve in this repo?**

**A:** It turns OpenClaw from a job-search script into a real telemetry source for AI agent security monitoring. The system watches untrusted job content, records ASI06 findings with evidence and session IDs, and exports digest-linked telemetry for later detector work. This answer shows you understand both the security goal and the operational pipeline.

**Q: Why use a real OpenClaw deployment instead of synthetic examples only?**

**A:** Synthetic data is useful for tests, but real job-board output reveals provider behavior, duplicate rates, zero-result paths, cron behavior, and telemetry gaps. The project still uses synthetic red-team data in tests, but the architecture is grounded in live runs. That demonstrates production thinking.

**Q: Why keep the ASI06 inline fallback after adding `detector.py`?**

**A:** The VPS deployment can still copy one script manually. If the `detections/` package is missing, the script should continue recording ASI06 checks instead of breaking. The fallback is temporary and should be removed after one normal cron confirms the detector-backed path. This shows safe cutover discipline.

## 6. Key Takeaways Section

- ClawGuard Phase 1 is running against real OpenClaw telemetry.
- ASI06 is the first implemented detector-backed risk class.
- ASI01 is documented but intentionally not runtime implemented yet.
- Clean runs are useful because they establish false-positive and operational baselines.
- The architecture favors evidence preservation over automated action.

## 7. Summary Reference Card

| Item | Value |
|---|---|
| Main runtime | `target-agent/skills/job-search-custom/job_search_secure.py` |
| Main detector | `detections/asi06_jd_content/detector.py` |
| Findings table | `job_security_findings` |
| Session ID format | `digest-YYYYMMDDTHHMMSS-xxxxxxxx` |
| Latest telemetry files | `/data/clawguard/telemetry/telemetry_latest.json`, `/data/clawguard/telemetry/telemetry_latest.md` |
| Core tests | `tests/test_job_search_secure.py`, `tests/test_asi06_detector.py` |

## 8. Next Steps

Study Lesson 01 next: OpenClaw runtime. Optional challenge: draw the pipeline on a whiteboard from memory, then check it against `README.md`.

Remember: ClawGuard is valuable because every detector is tied to evidence, not vibes. 🛡️
