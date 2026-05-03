# ASI06 JD Content Detection

Status: Detector module implemented; OpenClaw runtime still inline

This module will house ClawGuard detection rules for adversarial or unsafe job-description content observed through the OpenClaw `job-search-custom` pipeline.

Detector implementation:

```text
detections/asi06_jd_content/detector.py
```

OpenClaw runtime enforcement currently remains inline in:

```text
target-agent/skills/job-search-custom/job_search_secure.py
```

The ClawGuard module preserves the runtime contract while keeping the deployed OpenClaw skill self-contained until a deploy-safe integration pass.

## Planned Rules

| Rule | Name | Status |
|---|---|---|
| ASI06-001 | Job Description Prompt Injection | Implemented in detector |
| ASI06-002 | Job Description PII Request | Implemented in detector |
| ASI06-003 | Job Description Skill Stuffing | Implemented in detector |
| ASI06-004 | Suspicious Apply Domain | Implemented in detector |

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

## Module API

```python
from detections.asi06_jd_content.detector import detect_job_content

findings = detect_job_content(job)
```

Each finding includes `rule_id`, `severity`, `message`, `evidence`, and `context`. Use `finding.to_record(agent_session_id=...)` when serializing into a SQLite-compatible record.

## Next Step

Wire the OpenClaw runtime to this detector in a deploy-safe pass, or keep the runtime inline until the next VPS deployment window. Three clean sessions have landed, so ASI01 is now scaffolded separately while ASI06 has the first importable detection engine module.
