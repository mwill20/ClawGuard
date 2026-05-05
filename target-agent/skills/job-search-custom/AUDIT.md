# Security Audit: job-search-custom

Last updated: 2026-05-05

## Summary

`job-search-custom` is a custom OpenClaw skill written to avoid the risky behavior of generic auto-apply skills. It now serves two purposes:

- Low-volume job-search maintenance for the user.
- Real OpenClaw telemetry generation for ClawGuard.

The active maintenance path is deliberately conservative: no auto-submit, no auto-prep, no JD enrichment, and no Oxylabs credit usage.

## Current Security Controls

| Control | Status | Notes |
|---|---|---|
| No automatic job-board submission | Enforced | Submission requires explicit human approval and confirmation code |
| Resume stays local | Enforced | Resume/profile data are used locally for scoring and materials |
| Application auto-prep disabled in cron | Enforced | Compile runs with `--no-prepare` |
| JD enrichment disabled in cron | Enforced | `CLAWGUARD_ENRICHMENT_DAILY_CAP=0` |
| Provider cost minimized | Enforced | Oxylabs disabled in maintenance mode |
| Provider fallback explicit | Enforced | Brave and USAJobs can be forced with `--provider` |
| Audit and telemetry retained | Enforced | SQLite, digest archives, cron logs, and ClawGuard telemetry |
| ASI06/ASI01/ASI02 detector modules | Enforced | Findings persisted to `job_security_findings` |

## Data Flow

```text
Search provider
  -> normalized job record
  -> SQLite jobs table
  -> deterministic scoring against local profile
  -> ASI06 content checks
  -> ASI01 goal-redirect classification
  -> ASI02 tool-misuse classification
  -> digest archive
  -> post-compile ClawGuard telemetry
```

Resume and contact details are not sent to search providers by this skill.

## Provider Review

| Provider | Current Role | Risk Notes |
|---|---|---|
| Brave Search | Active maintenance provider | Uses API key; returns web search results, not resume data |
| USAJobs native API | Active for USAJobs | Requires auth key and registered user-agent email |
| Oxylabs | Supported but disabled | Prior 400 response deferred for isolated debug |

## Security Findings Model

Findings are stored in `job_security_findings` with:

```text
job_id
agent_session_id
rule_id
severity
message
evidence
context
detected_at
```

Prompt-injection evidence includes:

```text
pattern
matched_text
snippet
```

This is enough for ClawGuard correlation and detector-backed Phase 2 review workflows.

## Main Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Malicious JD attempts prompt injection | ASI06 prompt-injection patterns record findings and evidence |
| Fake job asks for sensitive personal data | ASI06 PII-request detector records findings |
| Keyword-stuffed posting inflates score | Skill-stuffing detector records finding and applies score penalty |
| Apply URL points to suspicious destination | Apply-domain mismatch detector records finding |
| Job content instructs unsafe tool use | ASI02 detector records unsafe egress, notification, shell, or file-write finding |
| Provider outage or block | Fallback providers and provider-specific logs |
| Cron generates too much activity during interviews | Daily minimal source set and 5-result cap |
| Telemetry file read during write | `telemetry_latest.*` written atomically by post-compile hook |

## Current Baseline

`digest-20260502T143953-c9eb7f4c` evaluated 22 jobs with:

- 0 ASI06 findings.
- 0 auto-prepared applications.
- 0 Oxylabs credits used.

That is the first clean-content ClawGuard baseline.

## Remaining Audit Items

- Confirm the first full scheduled cron chain updates `telemetry_latest.*` after 9:30 AM PT.
- Review any first live ASI06, ASI01, or ASI02 finding before using it as curated training evidence.
- Keep Oxylabs debugging isolated from the maintenance pipeline.
