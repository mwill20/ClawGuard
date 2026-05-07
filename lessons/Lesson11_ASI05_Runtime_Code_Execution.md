# Lesson 11: The Command Ledger - ASI05 Runtime Detector

## Welcome Back, Runtime Security Engineer

Goal: learn how ClawGuard detects unexpected process and container behavior from
runtime events.

Time estimate: 40 minutes

Prerequisites:

- Complete Lesson 09.
- Understand that ASI02 is content-side and ASI05 is runtime-side.
- Know that positive fixtures are local-only.

Why this matters: ASI05 is not "a job post mentioned Bash." ASI05 is about what
the runtime actually executed or controlled.

## 1. Introduction Section

### Learning objectives

- Explain the difference between ASI02 and ASI05.
- Run the ASI05 positive runtime fixture.
- Prove clean cron wrapper behavior produces zero findings.
- Inspect process/container evidence fields.
- Explain why raw commands and container IDs are not stored.
- Describe why enforcement remains out of scope.

### Plain-English explanation

ASI05 is the command ledger. It reviews runtime event labels for process and
container actions, then flags labels outside the approved inventory.

### Project currently implements

- Detector: `detections/asi05_code_execution/detector.py`
- Positive fixture: `examples/runtime_events_asi05_positive.json`
- Combined fixture: `examples/runtime_events_asi03_asi05_combined.json`
- Evaluator: `scripts/evaluate_runtime_detectors.py`
- Tests: `tests/test_asi05_runtime_detector.py`

### Recommended (not implemented here)

- Runtime blocking.
- Full command-line capture.
- Container mutation enforcement.
- SQLite persistence for runtime findings.

## 2. Key Concepts Section

| Term | Meaning |
|---|---|
| Process label | A safe label for a command category, not the raw command. |
| Container action | A safe label for expected container work, not a container ID. |
| Approved inventory | Known-safe process/container labels from normal ops. |
| ASI05 finding | Runtime evidence of unexpected execution behavior. |

Project currently implements two ASI05 rules:

| Rule | Trigger |
|---|---|
| `ASI05_UNAPPROVED_PROCESS_LABEL` | A `process_exec` event has an unapproved command label or operation. |
| `ASI05_UNAPPROVED_CONTAINER_ACTION` | A `container_action` event has an unapproved container label or operation. |

Recommended (not implemented here):

- Detecting execution derived from untrusted content.
- Cron modification detection.
- Sensitive file mutation detection.

## 3. Code Walkthrough Section

### Approved labels

File: `detections/asi05_code_execution/detector.py`

```python
APPROVED_PROCESS_LABELS = {
    "python unittest discover",
    "evaluate asi06 fixture",
    "evaluate asi02 fixture",
    "evaluate combined detector fixture",
    "validate telemetry sample",
    "validate runtime events",
    "cron-wrapper-search-run",
    "cron-wrapper-compile-run",
}
```

This inventory protects normal validation and cron behavior from false positives.

### Process rule

```python
if label in self.approved_process_labels or operation in self.approved_process_labels:
    return None

severity = "HIGH" if policy_decision(event) == "review" else "MEDIUM"
return RuntimeDetectionFinding(
    rule_id="ASI05_UNAPPROVED_PROCESS_LABEL",
```

The detector checks both target label and operation label. Approved labels are
clean; unknown labels produce findings.

### Container rule

```python
if label in self.approved_container_labels and operation in self.approved_container_operations:
    return None
```

Container actions require both an approved container label and an approved
operation. This prevents a known container label from hiding an unexpected
operation.

## 4. Hands-On Exercises Section

Run from repo root:

```powershell
Set-Location C:\Projects\ClawGuard
```

### Exercise 1: Evaluate the ASI05 positive fixture

```powershell
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_asi05_positive.json --expected-micro-f1 1.0 --hide-timing
```

Expected output includes:

```json
{
  "agent_session_id": "digest-20260507T180500-a5105001",
  "exact_match": true,
  "expected_rule_ids": [
    "ASI05_UNAPPROVED_CONTAINER_ACTION",
    "ASI05_UNAPPROVED_PROCESS_LABEL"
  ],
  "micro": {
    "f1": 1.0,
    "fn": 0,
    "fp": 0,
    "precision": 1.0,
    "recall": 1.0,
    "tp": 2
  }
}
```

### Exercise 2: Prove the curated runtime baseline stays clean

```powershell
python -B scripts\evaluate_runtime_detectors.py --input lessons\runtime-events\2026-05\digest-20260507T174059-2121b8be\runtime_events.json --expect-no-findings --hide-timing
```

Expected output includes:

```json
{
  "exact_match": true,
  "expected_rule_ids": [],
  "predicted_rule_ids": []
}
```

### Exercise 3: Run ASI05 tests

```powershell
python -B -m unittest tests.test_asi05_runtime_detector
```

Expected output:

```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.004s

OK
```

## 5. Interview Preparation Section

**Q: How is ASI05 different from ASI02 in this project?**

**A:** ASI02 detects job content that tries to cause tool misuse before the
action happens. ASI05 evaluates runtime events showing process or container
actions that actually occurred or were recorded.

**Q: Why does ASI05 store labels instead of raw commands?**

**A:** Raw commands can expose secrets, paths, hostnames, and container details.
Labels give enough signal for detector logic while preserving operational
privacy.

**Q: Why does the container rule require both container label and operation to be approved?**

**A:** A known container label alone is not enough. The action also has to be an
approved operation, otherwise normal infrastructure names could hide unexpected
control behavior.

## 6. Key Takeaways Section

- ASI05 v1 detects unapproved process and container labels.
- Clean cron wrapper labels must stay clean.
- Runtime findings are observe-only.
- ASI05 does not duplicate ASI02 shell-content detection.
- Positive fixtures remain local-only.

## 7. Summary Reference Card

| Area | Reference |
|---|---|
| Detector | `detections/asi05_code_execution/detector.py` |
| Positive fixture | `examples/runtime_events_asi05_positive.json` |
| Clean baseline | `lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json` |
| Evaluator | `scripts/evaluate_runtime_detectors.py` |
| Rules | `ASI05_UNAPPROVED_PROCESS_LABEL`, `ASI05_UNAPPROVED_CONTAINER_ACTION` |
| Error behavior | Invalid runtime-event shape fails validation before evaluation. |

## 8. Next Steps

Next, wait for scheduled runtime-event confirmation from the daily cron. Optional
challenge: add a local-only fixture for sensitive file mutation and keep it
deferred until file mutation summaries are designed.
