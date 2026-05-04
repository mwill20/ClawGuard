# Phase 2 — ASI02 Tool Misuse Detection (Spec)

Last updated: 2026-05-04
Status: Spec; no runtime code yet
Predecessor: ASI06 (`detections/asi06_jd_content/`), ASI01 (`detections/asi01_goal_hijack/`)

## Context

Phase 1 detection coverage protects against adversarial *content* (ASI06) and adversarial *goal redirection* derived from that content (ASI01). The remaining gap is adversarial *tool use* — content or instructions that try to push the agent toward operations outside its intended scope.

For the OpenClaw job-search target, the realistic tool surface is small but non-trivial:

| Tool | Used for | Misuse risk |
|---|---|---|
| HTTP egress (Brave, USAJobs, apply URLs) | Search and enrichment | Egress to attacker-controlled host (data exfil, beaconing) |
| Filesystem writes | Digests, applications, telemetry | Writes outside `/data/clawguard/`, leaking artifacts |
| Notifications (email, Telegram) | Daily digest | Redirect digest content to attacker's address |
| Shell (`staggered_cron.sh`) | Cron orchestration | Arbitrary command injection via env or job content |

ASI02 v1 covers the content-side of this: it inspects job content and prepared materials for instructions that would direct the agent to use tools improperly. Phase 3 will add tool-call instrumentation for runtime-side detection.

## Threat Model

The threat actor controls untrusted inputs that flow through the OpenClaw pipeline:

- Job titles and descriptions returned from search providers.
- URLs in apply links.
- Cover-letter and resume-bullet template inputs (during prepare).
- Future: enriched JD bodies pulled by `enrich_top_jobs`.

The actor wants the agent to:

1. Fetch attacker-controlled URLs (data exfil channel).
2. Embed attacker payloads in cover letters or application packages.
3. Forward digest output to an attacker-controlled email or messaging endpoint.
4. Execute a shell-style payload via templating or environment injection.

ASI02 fires when the content carries a credible attempt to drive any of these.

## Rule Set (v1)

The rule_id prefix is `ASI02_*`. All evidence preserves `pattern`, `matched_text`, and `snippet` for parity with ASI06.

| rule_id | Severity | Trigger | Layer |
|---|---|---|---|
| `ASI02_EGRESS_REDIRECT` | HIGH | Imperative-style instruction to fetch / curl / wget a URL outside the safe-apply allowlist | Layer 1 (regex on content) + Layer 2 (URL allowlist) |
| `ASI02_NOTIFY_REDIRECT` | HIGH | Instruction to send digest, results, or summary to a specific email / phone / endpoint | Layer 1 (regex on content) |
| `ASI02_SHELL_INJECTION` | HIGH | Shell metacharacter sequences in fields used during template rendering or filenames (`;`, `&&`, `||`, backticks, `$(...)`) | Layer 1 (regex on content) |
| `ASI02_FILE_PATH_REDIRECT` | MEDIUM | Instruction to write output to absolute or parent-relative paths outside `/data/clawguard/` | Layer 1 (regex on content) |

### Why content-only for v1

The ClawGuard runtime currently doesn't emit structured tool-call events. Building Layer 3/4 ASI02 (allowlist enforcement, behavioral diff) requires a tool-call telemetry hook — a Phase 3 task. Until then, ASI02 v1 catches the *pre-action* content that *would* drive misuse, which is the same posture ASI06 takes for content-injection.

### Corroboration with ASI01

ASI02 findings should set `evidence.related_asi06_rule_id` and `evidence.related_asi01_rule_id` when ASI06/ASI01 also fired on the same content. Goal-redirect classifiers (ASI01) often signal the *intent*; ASI02 signals the *operation* the attacker wants. Surfacing both gives reviewers a complete picture.

## Module Layout

```text
detections/asi02_tool_misuse/
    __init__.py               # exports detector, finding dataclass
    detector.py               # ASI02ToolMisuseDetector class
    README.md                 # rule overview
    ASI02-001.md              # egress-redirect rule
    ASI02-002.md              # notify-redirect rule
    ASI02-003.md              # shell-injection rule
    ASI02-004.md              # file-path-redirect rule
```

The detector follows the ASI06 pattern exactly:

```python
class ASI02ToolMisuseDetector:
    def __init__(self, safe_egress_domains: set[str] | None = None,
                 safe_data_root: str = "/data/clawguard"):
        ...

    def detect(self, job, jd_text=None,
               asi06_findings=None, asi01_findings=None) -> list[DetectionFinding]:
        ...
```

It reuses `JobContent.from_any` and `_pattern_evidence` from `detections.asi06_jd_content.detector` to keep evidence shape consistent.

## Runtime Integration

Add to `target-agent/skills/job-search-custom/job_search_secure.py::run_jd_security_detections` after the ASI01 block:

```python
asi02_detector = ClawGuardASI02ToolMisuseDetector()
asi02_raw = asi02_detector.detect(
    job, jd_text=text,
    asi06_findings=asi06_raw,
    asi01_findings=asi01_raw,
)
asi02_findings = [_security_finding_from_clawguard(f) for f in asi02_raw]
return asi06_findings + asi01_findings + asi02_findings
```

Update `JobDatabase.record_security_findings` to include `ASI02_%` in the DELETE-then-replace clause.

Update `scripts/deploy_openclaw_skill.ps1` to py_compile `detections/asi02_tool_misuse/detector.py`.

Update `scripts/check_cron_confirmation.ps1` to look for `"ClawGuard ASI02 detector module active"`.

## Tests

Add to `tests/test_job_search_secure.py`:

- `test_asi02_egress_redirect_fires_on_unsafe_url_instruction`
- `test_asi02_notify_redirect_fires_on_email_redirect`
- `test_asi02_shell_injection_fires_on_metacharacter_payload`
- `test_asi02_silent_on_clean_content`
- `test_asi02_persists_with_session_id_and_corroboration_links`

Add a synthetic fixture at `examples/asi02_labeled_eval.json` with at least:

- 2 clean jobs (negative)
- 1 job per ASI02 rule (positive)
- 1 multi-rule combo job (positive)

Wire the fixture into `scripts/preflight.ps1` alongside the existing ASI06 evaluator step.

## Verification

End-to-end Phase 2 verification:

1. Local: `.\scripts\preflight.ps1` shows 25+ tests, ASI02 fixture eval at 1.0.
2. Deploy: `.\scripts\deploy_openclaw_skill.ps1` succeeds with ASI02 module py_compile.
3. Cron confirmation: `.\scripts\check_cron_confirmation.ps1` exits 0 with ASI02 detector activation visible in compile log.
4. Live: a synthetic test JD with an `http://attacker.example/exfil` instruction triggers `ASI02_EGRESS_REDIRECT` in the next digest run, persists with `agent_session_id` and corroboration links.

## Open Questions

These should be answered before implementation begins:

1. Which `safe_egress_domains` belong in the default allowlist? Currently ASI06 uses 14 apply-domain values; ASI02 may need a stricter list.
2. Should `ASI02_FILE_PATH_REDIRECT` look only at content text, or also at runtime arguments? Latter requires Phase-3 instrumentation.
3. How aggressive should `ASI02_SHELL_INJECTION` be on cybersecurity job postings, where shell snippets in JDs are common? Likely needs MEDIUM severity and a corroboration requirement (similar to ASI01's high-confidence-only path).
