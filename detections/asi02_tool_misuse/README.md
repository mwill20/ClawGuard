# ASI02 Tool Misuse Detection

Status: v1 implemented as content-side pre-action detection.

`detections/asi02_tool_misuse/detector.py` detects untrusted job content that
tries to make OpenClaw misuse tools before any action is taken. It follows the
ASI06/ASI01 detector pattern and returns evidence-preserving
`DetectionFinding` records.

## v1 Rules

| rule_id | Severity | Purpose |
|---|---|---|
| `ASI02_EGRESS_REDIRECT` | HIGH | Unsafe `curl`, `wget`, fetch, upload, post, or beacon instruction |
| `ASI02_NOTIFY_REDIRECT` | HIGH | Instruction to send digest, resume, summary, or user data to an external destination |
| `ASI02_SHELL_INJECTION` | MEDIUM/HIGH | Shell-style payload in untrusted content |
| `ASI02_FILE_PATH_REDIRECT` | MEDIUM | Instruction to write output outside `/data/clawguard/` |

## Runtime Boundary

ASI02 v1 does not observe live tool calls. It detects content that would drive
tool misuse. Runtime tool-call instrumentation remains Phase 3.

## Evidence Contract

Every ASI02 finding includes:

- `attempted_operation_category`
- `matches[].pattern`
- `matches[].matched_text`
- `matches[].snippet`
- rule-specific destination fields such as `destination_url`, `destination`, or `target_path`
- optional `related_asi06_rule_id`
- optional `related_asi01_rule_id`
