# 🎓 Lesson 01: The Job-Search Command Center - OpenClaw Runtime

## 🛡️ Welcome Back, Runtime Engineer

Goal: understand how `job_search_secure.py` collects jobs, scores them, records security findings, and compiles digest telemetry.

Time estimate: 45 minutes

Prerequisites:

- Complete Lesson 00.
- Run commands from `C:\Projects\ClawGuard`.
- Know basic Python dataclasses and command-line arguments.

Why this matters: `job_search_secure.py` is the live OpenClaw skill. If you can explain this file, you can explain how ClawGuard gets real data.

## 1. Introduction Section

### Learning objectives

- Locate the runtime entry points in `job_search_secure.py`.
- Explain how source search, scoring, digesting, and findings connect.
- Trace the required detector-backed ASI06 path.
- Explain the purpose of `agent_session_id`.
- Identify the low-volume maintenance controls.
- Describe what should and should not happen during cron.

### Plain-English explanation

`job_search_secure.py` is the command center. It searches job sources, stores results, scores jobs against the profile, runs ASI06 checks, writes findings to SQLite, and compiles daily digest output.

Analogy: this file is air traffic control. Job sources are planes, SQLite is the runway log, ASI06 is the safety scanner, and the digest is the daily flight board.

### Project implements

- Runtime file: `target-agent/skills/job-search-custom/job_search_secure.py`
- Detector import: line 41
- Logging setup: lines 208-218
- Session ID helper: line 281
- DB class: line 288
- Provider order: line 1127
- Search parsing: lines 1191 and 1254
- ASI06 runtime switch: lines 1673-1687
- Scoring: line 1692
- Daily digest: line 2067
- CLI main: line 2322

### Recommended (not implemented here)

- Package installation instead of manual file copy.
- CLI subcommands split into smaller files.
- Structured JSON logging for every runtime event.
- Runtime health endpoint for the OpenClaw skill.

## 2. Key Concepts Section

### Terms

| Term | Definition |
|---|---|
| Provider | The search backend: Brave, USAJobs, or Oxylabs when enabled. |
| Site | The source platform key: `linkedin`, `cybersecjobs`, `usajobs`. |
| Digest | The daily compiled summary of scored jobs and session metadata. |
| Score | Match percentage against profile skills, certs, title, and location. |
| Finding | A detector event written into `job_security_findings`. |

### Design decisions

Project implements:

- `CLAWGUARD_DISABLE_OXYLABS=1` for zero-credit maintenance mode.
- `CLAWGUARD_ENRICHMENT_DAILY_CAP=0` to avoid paid/full-JD enrichment.
- `--no-prepare` in cron compile so application materials are not created automatically.
- Detector-backed ASI06 runtime with packaged deployment required.

Recommended (not implemented here):

- Schema/policy checks before accepting job records from providers.
- Quarantine for job descriptions before future LLM summarization.
- Semantic review for ambiguous prompt-injection language.

## 3. Code Walkthrough Section

### Detector import

File: `target-agent/skills/job-search-custom/job_search_secure.py:41`

```python
from detections.asi06_jd_content.detector import ASI06JobContentDetector as ClawGuardASI06JobContentDetector
```

Line-by-line:

1. `from detections...` imports the standalone ClawGuard detector.
2. `as ClawGuardASI06JobContentDetector` keeps the adapter name stable inside the OpenClaw runtime.

Why: after VPS cron confirmed the detector-backed path, missing `detections/` is treated as a packaging error instead of silently falling back to duplicate inline logic.

### Session ID helper

File: `target-agent/skills/job-search-custom/job_search_secure.py:281`

```python
def new_agent_session_id(prefix: str = "digest") -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
```

This creates IDs like `digest-20260503T163003-b91b67e1`.

Why:

- Timestamp makes logs searchable.
- UUID suffix prevents same-second collisions.
- Prefix lets future session types reuse the helper.

### ASI06 runtime switch

File: `target-agent/skills/job-search-custom/job_search_secure.py:1673`

```python
def run_jd_security_detections(job: Job, jd_text: Optional[str] = None) -> List[SecurityFinding]:
    global ASI06_DETECTOR_MODE_LOGGED
    text = jd_text if jd_text is not None else f"{job.title}\n{job.description}"
    if not ASI06_DETECTOR_MODE_LOGGED:
        logger.info("ClawGuard ASI06 detector module active")
        ASI06_DETECTOR_MODE_LOGGED = True
    detector = ClawGuardASI06JobContentDetector(
        skill_stuffing_threshold=ASI06_SKILL_STUFFING_THRESHOLD
    )
    return [
        _security_finding_from_clawguard(finding)
        for finding in detector.detect(job, jd_text=text)
    ]
```

What it does:

1. Builds the text inspected by ASI06.
2. Logs a one-time production proof line.
3. Instantiates the detector with the runtime threshold.
4. Converts detector findings into the legacy `SecurityFinding` shape.

Why: this keeps ASI06 logic in one importable module while preserving the existing OpenClaw `SecurityFinding` storage shape.

### Daily digest flow

File: `target-agent/skills/job-search-custom/job_search_secure.py:2067`

```python
def run_daily_digest(
    site: Optional[str] = None,
    compile_only: bool = False,
    sites: Optional[List[str]] = None,
    budget_limit: int = 50,
    max_results_per_site: int = DIGEST_MAX_RESULTS_PER_SITE,
    min_score: float = MIN_SCORE_THRESHOLD,
    auto_prepare: bool = True,
    send_notification: bool = True,
    output_format: str = "json",
    provider: Optional[str] = None,
) -> Dict:
```

What it does:

1. `site` supports staggered single-source cron runs.
2. `compile_only` lets the 9:30 job build the digest without searching again.
3. `budget_limit` keeps external provider usage controlled.
4. `auto_prepare` is disabled in cron.
5. `output_format` controls JSON, Telegram, or email-style output.

Edge case: a post-daily manual compile can return 0 jobs because the daily window has already been processed. That is expected and still proves startup/import behavior.

## 4. Hands-On Exercises Section

### 🧪 Exercise 1: Verify the runtime imports

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c "import importlib.util, sys; from pathlib import Path; script=Path('target-agent/skills/job-search-custom/job_search_secure.py'); spec=importlib.util.spec_from_file_location('job_search_secure', script); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); print(m.ClawGuardASI06JobContentDetector.__module__ if m.ClawGuardASI06JobContentDetector else 'fallback')"
```

Expected output:

```text
detections.asi06_jd_content.detector
```

### 🧪 Exercise 2: Generate a session ID

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c "import importlib.util, sys; from pathlib import Path; script=Path('target-agent/skills/job-search-custom/job_search_secure.py'); spec=importlib.util.spec_from_file_location('job_search_secure', script); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); print(m.new_agent_session_id())"
```

Expected output shape:

```text
digest-20260503T163003-b91b67e1
```

The exact timestamp and suffix will differ.

### 🧪 Exercise 3: Run the runtime tests

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest tests.test_job_search_secure
```

Expected output:

```text
.........
----------------------------------------------------------------------
Ran 9 tests in 0.0

OK
```

Note: the exact seconds may vary.

### 🧪 Exercise 4: Intentional packaging failure

PowerShell:

```powershell
Set-Location C:\tmp
python -B -c "import importlib.util, sys; from pathlib import Path; script=Path('C:/Projects/ClawGuard/target-agent/skills/job-search-custom/job_search_secure.py'); spec=importlib.util.spec_from_file_location('job_search_secure', script); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)"
```

Expected output includes:

```text
ModuleNotFoundError: No module named 'detections'
```

Why this matters: missing `detections/` is now a deployment error. Run future commands from the repo root or deploy the package with the runtime script.

## 5. Interview Preparation Section

**Q: Why is `job_search_secure.py` still important after creating `detector.py`?**

**A:** `detector.py` owns ASI06 logic, but `job_search_secure.py` is still the live orchestration layer. It searches, scores, stores, compiles, and calls the detector. This shows you understand module boundaries.

**Q: What is the purpose of `agent_session_id`?**

**A:** It ties a digest run to security findings. Without it, you could know a finding exists but not which run produced it. The timestamp plus UUID format makes it both readable and collision-resistant.

**Q: Why does missing `detections/` fail fast now?**

**A:** The VPS cron already confirmed the detector module path. Failing fast prevents duplicate inline logic from drifting away from the detector and makes incomplete deployment packaging obvious.

## 6. Key Takeaways Section

- `job_search_secure.py` is the live runtime command center.
- It now requires the standalone ASI06 detector.
- Runtime mode logging proves whether the detector path is active.
- Digest sessions create the correlation boundary for telemetry.
- Low-volume flags are intentional operational guardrails.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| Entry point | `python3 job_search_secure.py digest` |
| Detector switch | `run_jd_security_detections()` |
| Session helper | `new_agent_session_id()` |
| Provider logic | `_provider_order()` |
| Parser tests | `test_brave_parser_extracts_title_company_when_present`, `test_usajobs_parser_maps_api_shape_to_job` |
| Runtime proof log | `ClawGuard ASI06 detector module active` |

## 8. Next Steps

Study Lesson 02 next: the ASI06 detector module. Optional challenge: add a packaged deploy helper that copies `job_search_secure.py` and `detections/` together.

Remember: runtime code is where architecture meets production constraints. 🛡️
