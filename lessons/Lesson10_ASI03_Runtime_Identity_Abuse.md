# Lesson 10: The Identity Notary - ASI03 Runtime Detector

## Welcome Back, Runtime Security Engineer

Goal: learn how ClawGuard detects identity and credential misuse from runtime
events.

Time estimate: 40 minutes

Prerequisites:

- Complete Lesson 09.
- Understand `runtime-events/0.1`.
- Know that these fixtures are local-only and never sent to live providers.

Why this matters: ASI03 is about identity and privilege abuse. In this project,
that means credential labels, identity context, and egress destinations. A
detector that guesses from job text would be noisy, so Phase 4 uses runtime
facts.

## 1. Introduction Section

### Learning objectives

- Explain what ASI03 means in ClawGuard.
- Run the ASI03 positive runtime fixture.
- Prove clean runtime baselines produce zero ASI03 findings.
- Inspect ASI03 evidence fields.
- Explain why raw secrets are never stored.
- Describe what remains recommended but not implemented.

### Plain-English explanation

ASI03 is the identity notary. It checks whether the runtime used an approved
credential label and whether credential use stayed paired with approved
provider egress.

### Project currently implements

- Detector: `detections/asi03_identity_abuse/detector.py`
- Positive fixture: `examples/runtime_events_asi03_positive.json`
- Combined fixture: `examples/runtime_events_asi03_asi05_combined.json`
- Evaluator: `scripts/evaluate_runtime_detectors.py`
- Tests: `tests/test_asi03_runtime_detector.py`

### Recommended (not implemented here)

- Runtime blocking for credential misuse.
- Raw secret inspection.
- LLM-as-judge identity reasoning.
- SQLite persistence for runtime findings.

## 2. Key Concepts Section

| Term | Meaning |
|---|---|
| Credential label | A safe name for a credential, not the secret value. |
| Approved inventory | The known-safe credential labels and egress domains. |
| Egress mismatch | Credential use appears with egress to a non-approved domain. |
| Runtime finding | A finding tied to `agent_session_id` and `event_id`, not `job_id`. |

Project currently implements two ASI03 rules:

| Rule | Trigger |
|---|---|
| `ASI03_UNKNOWN_CREDENTIAL_LABEL` | A `credential_use` event has a label outside the approved inventory. |
| `ASI03_CREDENTIAL_EGRESS_MISMATCH` | An unapproved credential label appears in a session with non-approved network egress. |

Recommended (not implemented here):

- Identity context switch detection.
- Secret path access detection.
- Scope escalation detection.

## 3. Code Walkthrough Section

### Detector inventory

File: `detections/asi03_identity_abuse/detector.py`

```python
APPROVED_CREDENTIAL_LABELS = {
    "brave-search-provider-credential",
    "usajobs-search-provider-credential",
}

APPROVED_EGRESS_DOMAINS = {
    "api.search.brave.com",
    "data.usajobs.gov",
}
```

This code defines the clean baseline. Normal Brave and USAJobs credentials and
domains should not alert.

### Unknown credential rule

```python
if not label or label in self.approved_credential_labels:
    continue
findings.append(RuntimeDetectionFinding(
    rule_id="ASI03_UNKNOWN_CREDENTIAL_LABEL",
    severity="MEDIUM",
    message="Runtime used a credential label outside the approved provider inventory.",
```

This code ignores empty or approved labels, then emits a finding for a label
outside the inventory. The evidence stores the label and approved inventory, not
the credential value.

### Credential egress mismatch

```python
unknown_credentials = [
    event for event in credential_events
    if event_label(event) and event_label(event) not in self.approved_credential_labels
]
external_egress = [
    event for event in egress_events
    if event_label(event) and event_label(event) not in self.approved_egress_domains
]
if not unknown_credentials or not external_egress:
    return None
```

The rule requires both sides: an unapproved credential label and non-approved
egress. This avoids alerting on normal provider traffic.

## 4. Hands-On Exercises Section

Run from repo root:

```powershell
Set-Location C:\Projects\ClawGuard
```

### Exercise 1: Evaluate the ASI03 positive fixture

```powershell
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_asi03_positive.json --expected-micro-f1 1.0 --hide-timing
```

Expected output includes:

```json
{
  "agent_session_id": "digest-20260507T180000-a5103001",
  "exact_match": true,
  "expected_rule_ids": [
    "ASI03_CREDENTIAL_EGRESS_MISMATCH",
    "ASI03_UNKNOWN_CREDENTIAL_LABEL"
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

### Exercise 2: Prove clean baselines stay clean

```powershell
python -B scripts\evaluate_runtime_detectors.py --input examples\runtime_events_normal_ops.json --expect-no-findings --hide-timing
```

Expected output includes:

```json
{
  "exact_match": true,
  "expected_rule_ids": [],
  "predicted_rule_ids": []
}
```

### Exercise 3: Run ASI03 tests

```powershell
python -B -m unittest tests.test_asi03_runtime_detector
```

Expected output:

```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.005s

OK
```

## 5. Interview Preparation Section

**Q: Why is ASI03 a runtime detector here instead of a job-text detector?**

**A:** Identity abuse requires facts about credential use, identity context, and
egress. Job text can mention credentials defensively, so text-only detection
would create false positives. Runtime events provide the right evidence.

**Q: Why store credential labels instead of credential values?**

**A:** Labels are enough to detect inventory drift while preventing secret
leakage. The detector can say "unknown credential label was used" without ever
handling raw secrets.

**Q: Why require both unknown credential and unknown egress for the HIGH rule?**

**A:** Corroboration reduces noise. A strange credential label alone is
important, but pairing it with non-approved egress is a stronger abuse signal.

## 6. Key Takeaways Section

- ASI03 v1 detects unknown credential labels and credential/egress mismatch.
- Clean Brave/USAJobs provider behavior must stay clean.
- Findings are session/event based.
- Persistence is deferred.
- Positive fixtures are local-only.

## 7. Summary Reference Card

| Area | Reference |
|---|---|
| Detector | `detections/asi03_identity_abuse/detector.py` |
| Positive fixture | `examples/runtime_events_asi03_positive.json` |
| Clean fixture | `examples/runtime_events_normal_ops.json` |
| Evaluator | `scripts/evaluate_runtime_detectors.py` |
| Rules | `ASI03_UNKNOWN_CREDENTIAL_LABEL`, `ASI03_CREDENTIAL_EGRESS_MISMATCH` |
| Error behavior | Invalid runtime-event shape fails validation before evaluation. |

## 8. Next Steps

Study Lesson 11 next: ASI05 unexpected code execution. Optional challenge:
add a local-only fixture for identity context switching, then keep it deferred
until the rule design is reviewed.
