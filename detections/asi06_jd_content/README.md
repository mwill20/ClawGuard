# ASI06 JD Content Detection

Status: Rule spec complete; runtime checks remain inline

This module will house ClawGuard detection rules for adversarial or unsafe job-description content observed through the OpenClaw `job-search-custom` pipeline.

Runtime enforcement currently remains inline in:

```text
target-agent/skills/job-search-custom/job_search_secure.py
```

The extraction is intentionally delayed until enough live telemetry exists to validate rule shape against real jobs, not synthetic examples only.

## Planned Rules

| Rule | Name | Status |
|---|---|---|
| ASI06-001 | Job Description Prompt Injection | Documented, inline runtime active |
| ASI06-002 | Job Description PII Request | Planned |
| ASI06-003 | Job Description Skill Stuffing | Planned |
| ASI06-004 | Suspicious Apply Domain | Planned |

## Telemetry Inputs

Primary source:

```sql
job_security_findings
```

Required fields:

- `job_id`
- `agent_session_id`
- `rule_id`
- `severity`
- `message`
- `evidence`
- `context`
- `detected_at`

Expected `context` JSON fields:

- `job_id`
- `job_title`
- `company`
- `source_platform`
- `apply_url`
- `source_field`

## Baseline

The first baseline is documented in:

```text
lessons/clawguard-telemetry-baseline-001.md
```

It recorded 22 jobs across LinkedIn and CyberSecJobs with 0 ASI06 findings. That zero-finding state is the initial clean-content baseline for future comparisons.

## Next Step

Keep this module as a rule contract until live findings justify extraction. If a confirmed ASI06 prompt-injection finding appears, extract the inline implementation from `job_search_secure.py` into this module. Three clean sessions have landed, so ASI01 is now scaffolded separately while ASI06 remains inline.
