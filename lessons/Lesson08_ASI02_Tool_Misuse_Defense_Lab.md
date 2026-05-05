# Lesson 08: The Tool-Use Gatekeeper - ASI02 Defense Lab

## Welcome Back, Runtime Security Engineer

Goal: learn how ClawGuard detects content that tries to push an agent into
unsafe tool use.

Time estimate: 45 minutes

Prerequisites:

- Complete Lessons 01, 02, 05, and 06.
- Understand that job descriptions are untrusted input.
- Know how to run Python commands from the repo root.

Why this matters: ASI06 asks "is the content adversarial?" ASI01 asks "is the
agent goal being redirected?" ASI02 asks "what unsafe operation is the attacker
trying to make the agent perform?"

## 1. Introduction Section

### Learning objectives

- Explain what ASI02 protects in this project.
- Run the ASI02 detector against clean and adversarial fixtures.
- Distinguish tool discussion from tool misuse instructions.
- Inspect ASI02 evidence fields.
- Trigger an intentional fixture-evaluation failure safely.
- Explain why runtime tool-call monitoring is deferred to Phase 3.

### Plain-English explanation

ASI02 v1 is a pre-action tool-misuse detector. It reads untrusted job content
and looks for instructions that would make OpenClaw misuse tools: fetch an
attacker URL, send a digest to an attacker, execute a shell payload, or write
output outside the safe data root.

Analogy: ASI02 is the gatekeeper at a tool room. It does not wait for someone
to pick up the tool; it flags the note that says "take this tool and use it in
an unsafe way."

### Project implements

- Detector: `detections/asi02_tool_misuse/detector.py`
- Runtime wiring: `target-agent/skills/job-search-custom/job_search_secure.py`
- Synthetic fixture: `examples/asi02_labeled_eval.json`
- Evaluator: `scripts/evaluate_asi02.py`
- Unit tests: `tests/test_asi02_detector.py`
- Runtime tests: `tests/test_job_search_secure.py`
- Telemetry schema support: `scripts/validate_telemetry.py` schema `1.2`

### Recommended (not implemented here)

- Runtime tool-call telemetry for actual command/network/file operations.
- Policy enforcement before a tool call executes.
- A curated real-world false-positive set.
- LLM-as-judge review for ambiguous tool-use intent.

## 2. Key Concepts Section

### Terms

| Term | Meaning |
|---|---|
| ASI02 | OWASP Agentic AI risk for tool misuse. |
| Content-side detection | Detecting unsafe instructions before a tool call occurs. |
| Egress redirect | Content tells the agent to fetch, upload, post, or beacon to an unsafe URL. |
| Notification redirect | Content tells the agent to send results, resume, or profile data to an external destination. |
| Shell injection | Content contains shell-style payloads such as `&& env` or `cat /etc/passwd`. |
| File path redirect | Content tells the agent to write output outside `/data/clawguard/`. |

### Design decisions

Project implements:

- ASI02 runs after ASI06 and ASI01.
- ASI02 receives ASI06/ASI01 findings as optional corroboration links.
- ASI02 does not treat every mention of `curl`, shell, APIs, or webhooks as an alert.
- ASI02 uses schema `1.2` evidence fields so telemetry readers know how to interpret the finding.

Recommended (not implemented here):

- Layer 3 tool-call enforcement that can block unsafe commands.
- Layer 4 semantic review for ambiguous content.
- Per-tool allowlists for HTTP, filesystem, notifications, and shell.

## 3. Code Walkthrough Section

### Detector entry point

File: `detections/asi02_tool_misuse/detector.py`

```python
class ASI02ToolMisuseDetector:
    """Detect content that attempts to drive unsafe tool use."""

    def detect(
        self,
        job: Any,
        jd_text: Optional[str] = None,
        asi06_findings: Optional[Iterable[Any]] = None,
        asi01_findings: Optional[Iterable[Any]] = None,
    ) -> list[DetectionFinding]:
```

What this does:

1. Accepts a job record or object.
2. Builds detection text from title and description unless `jd_text` is passed.
3. Accepts upstream ASI06 and ASI01 findings for corroboration.
4. Returns a list of `DetectionFinding` records.

Why: this mirrors the ASI06/ASI01 detector pattern, so runtime integration stays
small and predictable.

### Rule execution order

```python
findings = [
    self.detect_egress_redirect(text, content.context, links),
    self.detect_notify_redirect(text, content.context, links),
    self.detect_shell_injection(text, content.context, links),
    self.detect_file_path_redirect(text, content.context, links),
]
```

What this does:

1. Checks unsafe HTTP egress.
2. Checks notification redirection.
3. Checks shell payloads.
4. Checks unsafe file-write destinations.

Why: ASI02 reports the operation category the attacker is trying to drive. A
single job can trigger multiple ASI02 findings.

### Runtime integration

File: `target-agent/skills/job-search-custom/job_search_secure.py`

```python
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

What this does:

1. Instantiates the ASI02 detector.
2. Passes ASI06 and ASI01 raw findings into ASI02.
3. Converts detector findings into runtime `SecurityFinding` objects.
4. Returns all detector families together.

Why: ASI06 provides content evidence, ASI01 provides goal intent, and ASI02
provides attempted operation type.

### Error handling and edge cases

Project implements:

- Safe egress domains avoid false positives for known maintenance providers.
- Clean tool mentions stay silent.
- Bare shell snippets are `MEDIUM`; dangerous sinks or imperative execution are `HIGH`.
- File writes under `/data/clawguard/` are treated as safe.

Recommended (not implemented here):

- Block decisions before execution.
- Process-level confirmation that a shell payload actually ran.
- Host-level telemetry for Docker, cron, and browser subprocesses.

## 4. Hands-On Exercises Section

### Exercise 1: Compare clean and combo samples

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -c "import json; from pathlib import Path; from detections.asi02_tool_misuse.detector import detect_tool_misuse; jobs=json.loads(Path('examples/asi02_labeled_eval.json').read_text()); selected=[job for job in jobs if job['job_id'] in ('asi02-clean-001','asi02-combo-001')]; print([(job['job_id'], [f.rule_id for f in detect_tool_misuse(job)]) for job in selected])"
```

Expected output:

```text
[('asi02-clean-001', []), ('asi02-combo-001', ['ASI02_EGRESS_REDIRECT', 'ASI02_NOTIFY_REDIRECT', 'ASI02_SHELL_INJECTION', 'ASI02_FILE_PATH_REDIRECT'])]
```

### Exercise 2: Run ASI02 detector unit tests

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest tests.test_asi02_detector
```

Expected output:

```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.003s

OK
```

### Exercise 3: Run ASI02 fixture evaluation

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B scripts\evaluate_asi02.py --input examples\asi02_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Expected output includes:

```text
"record_count": 7
"exact_match_accuracy": 1.0
"precision": 1.0
"recall": 1.0
"f1": 1.0
```

### Exercise 4: Trigger an intentional threshold failure

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B scripts\evaluate_asi02.py --input examples\asi02_labeled_eval.json --expected-micro-f1 1.1 --hide-timing
```

Expected output includes:

```text
micro F1 1.0 is below expected 1.1
```

Why this failure is useful: it proves the evaluator exits non-zero when the
quality gate is not met.

### Exercise 5: Validate the first curated clean baseline

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B scripts\validate_telemetry.py --input lessons\telemetry\2026-05\digest-20260505T163003-d9133ff9\telemetry.json
```

Expected output:

```json
{
  "agent_session_id": "digest-20260505T163003-d9133ff9",
  "finding_count": 0,
  "rule_count_keys": [],
  "schema_version": "1.0",
  "status": "valid"
}
```

Why this matters: ASI02 needs clean real telemetry as much as adversarial
fixtures. A zero-finding curated session proves the export, redaction,
validation, and lesson artifact path works without adding synthetic attacker
content to live providers.

## 5. Interview Preparation Section

**Q: Why is ASI02 content-side only in Phase 2?**

**A:** The current OpenClaw target does not emit structured tool-call events.
ASI02 v1 catches unsafe instructions before action, but runtime enforcement
requires tool-call or process telemetry. This answer shows you understand the
difference between pre-action detection and runtime enforcement.

**Q: Why does a clean job mentioning curl not trigger ASI02?**

**A:** Security roles can legitimately require API testing and shell scripting.
The detector looks for imperative misuse language and unsafe destinations, not
mere tool vocabulary. This demonstrates false-positive discipline.

**Q: What evidence makes an ASI02 finding useful to a reviewer?**

**A:** `attempted_operation_category`, matched text, snippet, destination field,
and optional ASI06/ASI01 corroboration links. That gives both the operation and
the intent context.

**Q: What would you build next for ASI02?**

**A:** Runtime tool-call telemetry with allowlist decisions and process/file
events. That would let ClawGuard tell whether unsafe instructions became unsafe
actions.

## 6. Key Takeaways Section

- ASI02 v1 detects unsafe tool-use instructions before actions happen.
- It covers HTTP egress, notifications, shell payloads, and file writes.
- It preserves evidence using the same review-friendly pattern as ASI06.
- It links to ASI06/ASI01 when content and goal signals corroborate.
- The first curated telemetry artifact is a clean baseline, not a positive ASI02 example.
- It does not claim runtime enforcement yet.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| Detector | `detections/asi02_tool_misuse/detector.py` |
| Runtime hook | `run_jd_security_detections()` |
| Fixture | `examples/asi02_labeled_eval.json` |
| Evaluator | `scripts/evaluate_asi02.py` |
| Tests | `tests/test_asi02_detector.py`, `tests/test_asi02_evaluation.py` |
| Telemetry schema | `1.2` |
| Curated clean baseline | `lessons/telemetry/2026-05/digest-20260505T163003-d9133ff9/telemetry.json` |
| Rule IDs | `ASI02_EGRESS_REDIRECT`, `ASI02_NOTIFY_REDIRECT`, `ASI02_SHELL_INJECTION`, `ASI02_FILE_PATH_REDIRECT` |
| Deferred | Runtime tool-call instrumentation and blocking |

## 8. Next Steps Section

Study the Phase 2 ASI03 and ASI05 roadmap specs next:

- `docs/plans/PHASE2_ASI03_IDENTITY_SPEC.md`
- `docs/plans/PHASE2_ASI05_CODE_EXEC_SPEC.md`

Optional challenge: add a clean fixture where a security role discusses
webhooks defensively, then prove ASI02 stays silent. That is how you keep
detectors useful instead of noisy.

Next curated-data challenge: add a finding-bearing or false-positive review
artifact under `lessons/telemetry/` after a real session warrants it. Do not
seed live job providers with synthetic attacker content just to create one.
