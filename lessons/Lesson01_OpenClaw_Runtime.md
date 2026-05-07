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
- Trace the required detector-backed ASI06, ASI01, and ASI02 paths.
- Explain the purpose of `agent_session_id`.
- Identify the low-volume maintenance controls.
- Describe what should and should not happen during cron.

### Plain-English explanation

`job_search_secure.py` is the command center. It searches job sources, stores results, scores jobs against the profile, runs ASI06/ASI01/ASI02 checks, writes findings to SQLite, and compiles daily digest output.

Analogy: this file is air traffic control. Job sources are planes, SQLite is the runway log, ClawGuard detectors are the safety scanners, and the digest is the daily flight board.

### Project implements

- Runtime file: `target-agent/skills/job-search-custom/job_search_secure.py`
- ASI06 detector import: line 41
- ASI01 detector import: line 42
- ASI02 detector import: line 43
- Logging setup: lines 204-218
- Session ID helper: line 283
- DB class: line 290
- Provider order: line 1130
- Search parsing: lines 1194 and 1257
- `search_site` with source-status semantics: lines 1364-1441
- Combined ASI06 + ASI01 + ASI02 detector switch: lines 1694-1725
- Scoring: line 1717
- Daily digest with `compile_only` log clarity: lines ~2090-2160
- CLI main: line ~2349

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
- Detector-backed ASI06, ASI01, and ASI02 runtime with packaged deployment required.

Recommended (not implemented here):

- Schema/policy checks before accepting job records from providers.
- Quarantine for job descriptions before future LLM summarization.
- Semantic review for ambiguous prompt-injection language.

## 3. Code Walkthrough Section

### Detector imports

File: `target-agent/skills/job-search-custom/job_search_secure.py:41-43`

```python
from detections.asi06_jd_content.detector import ASI06JobContentDetector as ClawGuardASI06JobContentDetector
from detections.asi01_goal_hijack.detector import ASI01GoalHijackDetector as ClawGuardASI01GoalHijackDetector
from detections.asi02_tool_misuse.detector import ASI02ToolMisuseDetector as ClawGuardASI02ToolMisuseDetector
```

Line-by-line:

1. `from detections...` imports the standalone ClawGuard detectors.
2. `as Claw...` keeps the adapter names stable inside the OpenClaw runtime.

Why: after VPS cron confirmed the detector-backed path for Phase 1 and Phase 2 added ASI02 to the same package boundary, missing `detections/` is treated as a packaging error. All active detectors are required at import time, so the runtime cannot start without them.

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

### Combined ASI06 + ASI01 + ASI02 detector switch

File: `target-agent/skills/job-search-custom/job_search_secure.py:1694`

```python
def run_jd_security_detections(job: Job, jd_text: Optional[str] = None) -> List[SecurityFinding]:
    global ASI06_DETECTOR_MODE_LOGGED, ASI01_DETECTOR_MODE_LOGGED, ASI02_DETECTOR_MODE_LOGGED
    text = jd_text if jd_text is not None else f"{job.title}\n{job.description}"
    if not ASI06_DETECTOR_MODE_LOGGED:
        logger.info("ClawGuard ASI06 detector module active")
        ASI06_DETECTOR_MODE_LOGGED = True
    asi06_detector = ClawGuardASI06JobContentDetector(
        skill_stuffing_threshold=ASI06_SKILL_STUFFING_THRESHOLD
    )
    asi06_raw = list(asi06_detector.detect(job, jd_text=text))
    asi06_findings = [_security_finding_from_clawguard(f) for f in asi06_raw]

    if not ASI01_DETECTOR_MODE_LOGGED:
        logger.info("ClawGuard ASI01 detector module active")
        ASI01_DETECTOR_MODE_LOGGED = True
    asi01_detector = ClawGuardASI01GoalHijackDetector()
    asi01_raw = asi01_detector.detect(job, jd_text=text, asi06_findings=asi06_raw)
    asi01_findings = [_security_finding_from_clawguard(f) for f in asi01_raw]

    if not ASI02_DETECTOR_MODE_LOGGED:
        logger.info("ClawGuard ASI02 detector module active")
        ASI02_DETECTOR_MODE_LOGGED = True
    asi02_detector = ClawGuardASI02ToolMisuseDetector()
    asi02_raw = asi02_detector.detect(
        job,
        jd_text=text,
        asi06_findings=asi06_raw,
        asi01_findings=asi01_raw,
    )
    asi02_findings = [_security_finding_from_clawguard(f) for f in asi02_raw]

    return asi06_findings + asi01_findings + asi02_findings
```

What it does:

1. Runs ASI06 first against the inspected text.
2. Logs a one-time activation line per detector for cron-confirmation visibility.
3. Passes the raw ASI06 findings into ASI01 as the corroboration upstream.
4. Passes ASI06 and ASI01 findings into ASI02 so tool-misuse findings can link back to related content or goal evidence.
5. Returns combined findings as the legacy `SecurityFinding` shape.

Why: ordering matters. ASI06 owns content patterns; ASI01 reads ASI06's output as upstream signal to classify *goal impact*; ASI02 reads both when classifying attempted operations. The combined return keeps the persistence layer (`record_security_findings`) indifferent to which rule produced each finding. See [Lesson 06](Lesson06_ASI01_Goal_Hijack_Scaffold.md) for ASI01 design rationale and [Lesson 08](Lesson08_ASI02_Tool_Misuse_Defense_Lab.md) for ASI02.

### Source-status semantics in `search_site`

File: `target-agent/skills/job-search-custom/job_search_secure.py:1404-1429`

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

What it does:

1. Computes the already-known count as `len(jobs) - new_count` (results returned minus newly inserted).
2. Picks one of four source statuses: `OK_NEW`, `ALL_KNOWN`, `EMPTY`, or (in the failure path on line 1437) `ERROR`.
3. Embeds the status into both the audit log JSON and the human-readable INFO line.

Why: before Phase 1 close, "source returned 10 already-known jobs" looked identical to "source returned nothing" in logs and audit events. Reviewers couldn't tell whether a quiet day meant the source was healthy (returning known content) or broken (returning nothing). The four-state status fixes that without a DB schema migration — the audit log JSON now carries the distinction. See [Lesson 07](Lesson07_Source_Compass_And_Phase2_Map.md) for the full rationale and Phase 2 follow-ups.

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

### 🧪 Exercise 1: Verify all detector imports

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c "import importlib.util, sys; from pathlib import Path; script=Path('target-agent/skills/job-search-custom/job_search_secure.py'); spec=importlib.util.spec_from_file_location('job_search_secure', script); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); print('asi06:', m.ClawGuardASI06JobContentDetector.__module__); print('asi01:', m.ClawGuardASI01GoalHijackDetector.__module__); print('asi02:', m.ClawGuardASI02ToolMisuseDetector.__module__)"
```

Expected output:

```text
asi06: detections.asi06_jd_content.detector
asi01: detections.asi01_goal_hijack.detector
asi02: detections.asi02_tool_misuse.detector
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
...............................
----------------------------------------------------------------------
Ran 31 tests in 0.267s

OK
```

Note: the exact seconds may vary. The 31 tests cover ASI06 detection, ASI01 goal-redirect classification, ASI02 tool-misuse detection, source-status audit, DB queryability, source discovery, and runtime-event hook emission.

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

**A:** Detector modules own ASI06/ASI01/ASI02 logic, but `job_search_secure.py` is still the live orchestration layer. It searches, scores, stores, compiles, and calls the detectors in dependency order. This shows you understand module boundaries.

**Q: What is the purpose of `agent_session_id`?**

**A:** It ties a digest run to security findings. Without it, you could know a finding exists but not which run produced it. The timestamp plus UUID format makes it both readable and collision-resistant.

**Q: Why does missing `detections/` fail fast now?**

**A:** The VPS cron already confirmed the detector module path. Failing fast prevents duplicate inline logic from drifting away from the detector and makes incomplete deployment packaging obvious.

## 6. Key Takeaways Section

- `job_search_secure.py` is the live runtime command center.
- It now requires the standalone ASI06, ASI01, and ASI02 detectors.
- Runtime mode logging proves whether the detector path is active.
- Digest sessions create the correlation boundary for telemetry.
- Low-volume flags are intentional operational guardrails.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| Entry point | `python3 job_search_secure.py digest` |
| Detector switch | `run_jd_security_detections()` (ASI06 + ASI01 + ASI02 combined) |
| Session helper | `new_agent_session_id()` |
| Provider logic | `_provider_order()` |
| Source-status audit field | `OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR` |
| Parser tests | `test_brave_parser_extracts_title_company_when_present`, `test_usajobs_parser_maps_api_shape_to_job` |
| Runtime proof logs | `ClawGuard ASI06 detector module active`, `ClawGuard ASI01 detector module active`, `ClawGuard ASI02 detector module active` |

## 8. Next Steps

Study [Lesson 02](Lesson02_ASI06_Detector.md) next: the ASI06 detector module. After that, [Lesson 06](Lesson06_ASI01_Goal_Hijack_Scaffold.md) covers the ASI01 corroborated classifier, [Lesson 07](Lesson07_Source_Compass_And_Phase2_Map.md) covers source-status semantics, and [Lesson 08](Lesson08_ASI02_Tool_Misuse_Defense_Lab.md) covers ASI02 tool-misuse detection.

Optional challenge: add a CLI flag `--source-status-min` that filters the digest to only show jobs from sources that returned `OK_NEW` (skipping `ALL_KNOWN` quiet days when manually compiling).

Remember: runtime code is where architecture meets production constraints. 🛡️
