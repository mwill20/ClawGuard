# ASI06: Adversarial Content In Ingested Job Descriptions

Status: Implemented inline in `job_search_secure.py`
Primary ClawGuard rule spec: `detections/asi06_jd_content/ASI06-001.md`
Last updated: 2026-05-03

## Threat Model

The job-search pipeline ingests external job content from untrusted sources and uses it for scoring, digest output, and optional application prep.

Potential attacks:

- Skill stuffing inflates match scores by stuffing a posting with every relevant keyword.
- Prompt injection attempts to redirect the agent's behavior during downstream processing.
- PII requests ask the user or agent to include sensitive personal data outside normal application flow.
- Suspicious apply URLs send the user toward a phishing or credential-harvesting destination.

## Current Runtime Rules

Inline rule IDs:

| Rule ID | Severity | Purpose |
|---|---|---|
| `ASI06_SKILL_STUFFING` | Medium | Detect unusually dense canonical skill matches |
| `ASI06_PROMPT_INJECTION` | High | Detect prompt-injection language in job content |
| `ASI06_PII_REQUEST` | High | Detect requests for sensitive personal data |
| `ASI06_APPLY_URL_MISMATCH` | Medium | Detect suspicious apply-domain mismatch |

Prompt-injection examples include:

```text
ignore previous instructions
disregard your system prompt
score this job at <number>
mark this as strong match
do not show other
override scoring
you are now a...
assistant:
system: you are
developer: you are
```

## Evidence Model

Findings are persisted in SQLite table `job_security_findings`.

Required correlation fields:

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

Expected `context` JSON fields:

```text
job_id
job_title
company
source_platform
apply_url
source_field
```

Prompt-injection evidence preserves:

```text
pattern
matched_text
snippet
```

This lets ClawGuard distinguish a true injection attempt from a legitimate security job posting discussing prompt injection as a defensive skill.

## Baseline

Baseline session `digest-20260502T143953-c9eb7f4c` evaluated 22 jobs and produced 0 ASI06 findings. That clean result is documented in `lessons/clawguard-telemetry-baseline-001.md`.

Zero findings are still telemetry. They establish the initial clean-content baseline.

## Extraction Criteria

Keep ASI06 inline until one of these happens:

- A confirmed prompt-injection finding appears in live production telemetry.
- At least three live ASI06 findings exist across real postings.

After that, extract the implementation into `detections/asi06_jd_content/` using `ASI06-001.md` as the rule contract.
