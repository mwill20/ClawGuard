# Lesson 09: The Flight Recorder - Runtime Event Monitoring

## Welcome Back, Runtime Security Engineer

Goal: learn how Phase 3 records what the agent actually did at runtime without
turning those facts into findings too early.

Time estimate: 50 minutes

Prerequisites:

- Complete Lessons 01, 04, 05, and 08.
- Know how `agent_session_id` connects digest, telemetry, and findings.
- Know how to run Python and PowerShell commands from the repo root.

Why this matters: ASI03 and ASI05 cannot be detected responsibly from job text
alone. They need runtime facts: identity context, credential labels, egress
domains, file writes, process labels, and container action labels.

## 1. Introduction Section

### Learning objectives

- Explain why runtime events are observe-only in Phase 3.
- Validate a curated runtime-event artifact with ASI03 and ASI05 readiness flags.
- Inspect the writer, host annotator, and export/redaction flow.
- Distinguish runtime evidence from runtime findings.
- Test an intentional schema failure safely.
- Describe what moves to Phase 4 detector promotion.

### Plain-English explanation

Runtime-event monitoring is ClawGuard's flight recorder. The job-search runtime
keeps doing its normal work, but it writes a structured record of important
actions so future detectors can reason about identity abuse and unexpected code
execution.

Analogy: an airplane flight recorder does not fly the plane and does not decide
who is at fault. It records enough trustworthy evidence that investigators can
understand what happened later.

### Project currently implements

- Writer: `target-agent/skills/job-search-custom/runtime_events.py`
- Runtime hooks: `target-agent/skills/job-search-custom/job_search_secure.py`
- Host wrapper annotator:
  `target-agent/skills/job-search-custom/clawguard_annotate_runtime_events.py`
- Host redactor:
  `target-agent/skills/job-search-custom/clawguard_redact_runtime_events.py`
- Cron wrapper: `target-agent/skills/job-search-custom/staggered_cron.sh`
- Export wrapper: `scripts/export_runtime_events.ps1`
- Validator: `scripts/validate_runtime_events.py`
- Full clean baseline:
  `lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json`

### Recommended (not implemented here)

- Runtime blocking or enforcement before observe-only telemetry proves stable.
- ASI03/ASI05 runtime detectors before clean and positive fixtures exist.
- Automated VPS-to-repo export without host-side redaction.
- LLM-as-judge review for ambiguous runtime sequences.

## 2. Key Concepts Section

### Terms

| Term | Meaning |
|---|---|
| `runtime-events/0.1` | The JSON schema version for Phase 3 runtime facts. |
| `agent_session_id` | Correlation ID shared by digest, telemetry, runtime events, and findings. |
| Observe-only | The system records facts but does not block, alert, or change behavior. |
| Host redaction | Sensitive cleanup performed on the VPS before copying artifacts locally. |
| Host annotation | Label-only facts appended by the cron wrapper after a container command exits. |
| ASI03 readiness | Evidence includes identity, credential, and egress facts. |
| ASI05 readiness | Evidence includes process/container/file-write facts. |

### Project currently implements

Phase 3 follows this flow:

```text
OpenClaw runtime
  -> runtime_events.py writes runtime-events/0.1 JSON
  -> staggered_cron.sh appends process/container labels
  -> clawguard_redact_runtime_events.py redacts on host
  -> export_runtime_events.ps1 copies redacted artifacts
  -> validate_runtime_events.py checks schema/readiness
  -> lessons/runtime-events/ stores curated baselines
```

Design decisions:

- Runtime events are disabled unless `CLAWGUARD_RUNTIME_EVENTS_ENABLED=1`.
- Events store labels, not raw secrets, raw commands, private paths, or host IDs.
- `flush_runtime_events()` writes both an archive file and `runtime_events_latest.json`.
- The host annotator updates both `latest` and the matching archive so
  export-by-session sees the same evidence.
- Policy decisions are event fields in Phase 3; standalone `policy_decision`
  events are deferred unless Phase 4 detectors need them.

### Recommended (not implemented here)

- Signed runtime-event artifacts.
- Sequence anomaly detection over event chains.
- Separate runtime-finding persistence tables.
- Per-tool enforcement policies for network, filesystem, shell, and container actions.

## 3. Code Walkthrough Section

### Runtime writer: session, record, flush

File: `target-agent/skills/job-search-custom/runtime_events.py`

Key lines to inspect:

- Line 22: `SCHEMA_VERSION = "runtime-events/0.1"`
- Lines 196-217: `start_runtime_event_session()`
- Lines 219-233: `record_runtime_event()`
- Lines 235-263: `_runtime_event_write_event()`
- Lines 265-297: `flush_runtime_events()`
- Line 299: `reset_for_tests()`

Actual code excerpt:

```python
def record_runtime_event(event: dict[str, Any]) -> bool:
    """Record a sanitized event into the active session.

    Returns False when runtime-event emission is disabled or no session has been
    started. This keeps Phase 3 observe-only instrumentation non-disruptive.
    """

    if _SESSION is None or not runtime_events_enabled():
        return False
    if _SESSION.flushed:
        raise RuntimeEventWriterError("cannot record runtime event after flush")

    _SESSION.events.append(_normalize_event(event, _SESSION))
    return True
```

Line-by-line:

1. `record_runtime_event(event)` accepts one event dictionary from the runtime.
2. The disabled/no-session branch returns `False` instead of raising. That keeps
   instrumentation non-disruptive.
3. The post-flush branch raises. Once a session is written, later mutation would
   create inconsistent evidence.
4. `_normalize_event()` adds required fields and performs safety checks before
   the event is stored.

Why this design: Phase 3 must not break job search. Missing optional telemetry
should be safe, but corrupted telemetry after flush should fail loudly in tests.

### Recursion guard: runtime-event file write

Actual code excerpt:

```python
def flush_runtime_events() -> Optional[Path]:
    """Flush the active session to disk and return the archive path.

    The self `file_write` event is appended directly here rather than through
    record_runtime_event(), avoiding recursive file_write self-emission.
    """

    if _SESSION is None or not runtime_events_enabled():
        return None
    if _SESSION.flushed:
        return _SESSION.archive_path

    if not _SESSION.self_write_recorded:
        _SESSION.events.append(_runtime_event_write_event(_SESSION))
        _SESSION.self_write_recorded = True
```

Line-by-line:

1. The disabled/no-session path returns `None`.
2. The already-flushed path returns the existing archive path. This makes flush
   idempotent.
3. The self `file_write` event is appended directly.
4. It does not call `record_runtime_event()` from inside the writer output path.

Common pitfall: if the writer recorded its own write through the normal record
function, it could recursively create file-write events forever.

### Host annotator: process and container labels

File:
`target-agent/skills/job-search-custom/clawguard_annotate_runtime_events.py`

Key lines to inspect:

- Lines 27-28: safe session and label regexes.
- Lines 123-181: `annotate_runtime_artifact()`.
- Lines 187-207: `annotate_latest_and_archive()`.

Actual code excerpt:

```python
process_event = _base_event(
    payload,
    event_type="process_exec",
    actor_id="cron-wrapper",
    operation=operation_label,
    operation_category="process-exec",
    target_kind="command_label",
    target_label=operation_label,
    policy_decision=policy_decision,
    policy_reason=policy_reason,
    evidence={
        "site_label": site_label,
        "exit_code": exit_code,
        "arguments_stored": "label_only",
        "cwd_label": "job-search-skill-dir",
    },
    sequence_offset=1,
)
```

Line-by-line:

1. `event_type="process_exec"` records that a wrapper process action occurred.
2. `operation=operation_label` stores a safe label such as
   `cron-wrapper-search-run`, not the raw command.
3. `target_kind="command_label"` tells reviewers the target is intentionally
   abstracted.
4. Evidence stores `exit_code`, `site_label`, and `arguments_stored`.

Why this design: ASI05 needs process evidence, but raw command lines can expose
secrets and infrastructure details. Label-only evidence gives detectors useful
context without leaking sensitive data.

### Cron wrapper: call the annotator after the command exits

File: `target-agent/skills/job-search-custom/staggered_cron.sh`

Key lines to inspect:

- Line 30: annotator host path.
- Line 55: reads `CLAWGUARD_RUNTIME_EVENTS_ENABLED`.
- Lines 67-83: `annotate_runtime_events()`.
- Lines 115 and 155: annotate compile/search wrapper runs.

Actual code excerpt:

```bash
annotate_runtime_events() {
    local operation_label="$1"
    local exit_code="$2"
    if [ "${RUNTIME_EVENTS_ENABLED:-}" = "1" ] && [ -x "$RUNTIME_EVENTS_ANNOTATOR" ]; then
        set +e
        python3 "$RUNTIME_EVENTS_ANNOTATOR" \
          --operation-label "$operation_label" \
          --site-label "$SITE" \
          --exit-code "$exit_code" \
          --container-label "job-search-runtime" \
          2>&1 | tee -a "$LOG_DIR/runtime_events_${DATE}.log"
```

Line-by-line:

1. The wrapper receives an operation label and exit code.
2. It runs only when runtime events are enabled and the annotator exists.
3. It passes labels, not raw commands or container IDs.
4. It logs annotation failures but does not hide the original job-search exit code.

Why this design: runtime monitoring is useful, but the cron wrapper still needs
to be reliable. Annotation failure should be visible without pretending the
original search/compile succeeded or failed differently.

## 4. Hands-On Exercises Section

Run these from the repo root:

```powershell
Set-Location C:\Projects\ClawGuard
```

### Exercise 1: Validate the full runtime baseline

PowerShell:

```powershell
python -B scripts\validate_runtime_events.py --input lessons\runtime-events\2026-05\digest-20260507T174059-2121b8be\runtime_events.json --require asi03 --require asi05
```

Bash:

```bash
python -B scripts/validate_runtime_events.py --input lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json --require asi03 --require asi05
```

Expected output:

```json
{
  "agent_session_id": "digest-20260507T174059-2121b8be",
  "event_count": 162,
  "event_type_counts": {
    "container_action": 1,
    "credential_use": 79,
    "file_write": 1,
    "identity_context": 1,
    "network_egress": 79,
    "process_exec": 1
  },
  "policy_decision_counts": {
    "allow": 161,
    "observe": 1
  },
  "required_readiness": [
    "asi03",
    "asi05"
  ],
  "schema_version": "runtime-events/0.1",
  "status": "valid"
}
```

### Exercise 2: Inspect the event types

PowerShell:

```powershell
python -B -c "import json; p='lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json'; data=json.load(open(p)); print(data['agent_session_id']); print(len(data['events'])); print(sorted({e['event_type'] for e in data['events']}))"
```

Bash:

```bash
python -B -c "import json; p='lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json'; data=json.load(open(p)); print(data['agent_session_id']); print(len(data['events'])); print(sorted({e['event_type'] for e in data['events']}))"
```

Expected output:

```text
digest-20260507T174059-2121b8be
162
['container_action', 'credential_use', 'file_write', 'identity_context', 'network_egress', 'process_exec']
```

### Exercise 3: Prove the validator catches broken correlation

PowerShell:

```powershell
python -B -c "import json; from pathlib import Path; src=Path('lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json'); tmp=Path('.tmp/clawguard-runtime-invalid.json'); tmp.parent.mkdir(exist_ok=True); data=json.loads(src.read_text()); data['events'][0].pop('agent_session_id', None); tmp.write_text(json.dumps(data, indent=2)); print(tmp)"
python -B scripts\validate_runtime_events.py --input .tmp\clawguard-runtime-invalid.json
```

Bash:

```bash
python -B -c "import json; from pathlib import Path; src=Path('lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/runtime_events.json'); tmp=Path('.tmp/clawguard-runtime-invalid.json'); tmp.parent.mkdir(exist_ok=True); data=json.loads(src.read_text()); data['events'][0].pop('agent_session_id', None); tmp.write_text(json.dumps(data, indent=2)); print(tmp)"
python -B scripts/validate_runtime_events.py --input .tmp/clawguard-runtime-invalid.json
```

Expected output:

```text
.tmp\clawguard-runtime-invalid.json
runtime event validation failed: runtime_events.events[0].agent_session_id is missing
```

### Exercise 4: Run the focused runtime-event tests

PowerShell:

```powershell
python -B -m unittest tests.test_runtime_event_host_annotation tests.test_runtime_event_contract tests.test_export_redaction
```

Bash:

```bash
python -B -m unittest tests.test_runtime_event_host_annotation tests.test_runtime_event_contract tests.test_export_redaction
```

Expected output:

```text
......................
----------------------------------------------------------------------
Ran 22 tests in 0.14s

OK
```

## 5. Interview Preparation Section

**Q: Why did Phase 3 emit runtime events before building ASI03 or ASI05 detectors?**

**A:** ASI03 and ASI05 are runtime risks. ASI03 needs identity, credential, and
egress facts. ASI05 needs process, container, and file-write facts. Building
detectors before the evidence exists would create guesswork or false positives.
Phase 3 records validated, redacted facts first, then Phase 4 can promote
detectors with clean and positive fixtures.

Why this demonstrates competence: you are explaining evidence-first security
engineering, not just naming OWASP categories.

**Q: Why does the host annotator use labels instead of raw command lines?**

**A:** Raw command lines can leak secrets, paths, hostnames, container IDs, and
deployment details. The annotator stores approved labels such as
`cron-wrapper-search-run`, `usajobs`, and `job-search-runtime`, plus the exit
code. That is enough for ASI05 baseline learning without exposing private
operational data.

Why this demonstrates competence: you understand both detection value and data
minimization.

**Q: What problem does `agent_session_id` solve here?**

**A:** It links runtime events to digest telemetry and security findings. A
reviewer can start from a digest session, inspect job findings, then inspect
runtime facts from the same run. Without this correlation anchor, telemetry
would be hard to query and easy to misinterpret.

Why this demonstrates competence: you connect schema design to incident review.

**Q: What is the main edge case in `flush_runtime_events()`?**

**A:** The writer needs to record that it wrote a runtime-event file, but calling
`record_runtime_event()` from inside the writer's output path could recursively
create more file-write events. The implementation directly appends one
self-write event before the atomic write.

Why this demonstrates competence: you noticed a production-grade telemetry
failure mode.

## 6. Key Takeaways Section

Project currently implements:

- Runtime events under `runtime-events/0.1`.
- Env-gated observe-only emission with `CLAWGUARD_RUNTIME_EVENTS_ENABLED=1`.
- Python runtime hooks for identity, credential, egress, and file-write facts.
- Host wrapper annotations for `process_exec` and `container_action`.
- Host-side redaction before export.
- Curated clean baselines for ASI03 and ASI05 readiness.

Recommended (not implemented here):

- ASI03 and ASI05 detector code.
- Runtime blocking or policy enforcement.
- Automated export from VPS to repo.
- Learned anomaly scoring over event sequences.

Critical details:

- Store labels, not raw secrets, commands, paths, or host IDs.
- Validate every exported artifact locally after host redaction.
- Treat clean baselines as false-positive controls, not findings.
- Keep synthetic malicious runtime fixtures local-only.

## 7. Summary Reference Card

| Area | Reference |
|---|---|
| Schema | `runtime-events/0.1` |
| Enable flag | `CLAWGUARD_RUNTIME_EVENTS_ENABLED=1` |
| Writer | `target-agent/skills/job-search-custom/runtime_events.py` |
| Writer functions | `start_runtime_event_session()`, `record_runtime_event()`, `flush_runtime_events()`, `reset_for_tests()` |
| Host annotator | `clawguard_annotate_runtime_events.py` |
| Host redactor | `clawguard_redact_runtime_events.py` |
| Export command | `.\scripts\export_runtime_events.ps1 -Sessions digest-20260507T174059-2121b8be` |
| Validate command | `python -B scripts\validate_runtime_events.py --input lessons\runtime-events\2026-05\digest-20260507T174059-2121b8be\runtime_events.json --require asi03 --require asi05` |
| Clean full baseline | `lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/` |
| Error behavior | Validator fails on missing IDs, raw secret-like fields, raw paths, inconsistent sessions, or missing readiness events. |

## 8. Next Steps Section

Study next:

- Lesson 08 if you need the content-side ASI02 detector flow.
- Phase 4 specs in `docs/plans/` when ASI03/ASI05 detector promotion begins.

Optional advanced topics:

- Add local-only positive ASI03 and ASI05 runtime-event fixtures.
- Design detector rules that score runtime sequences without storing raw secrets.
- Add a separate runtime findings table only after detector outputs stabilize.

Hands-on modification challenges:

- Add a clean deploy-helper event fixture without raw container IDs.
- Extend `examples/runtime_events_normal_ops.json` with one more allowed event.
- Add a validator test that rejects a raw command-looking evidence field.

Remember: Phase 3 records facts. Phase 4 decides which facts become findings.
