# ASI06 JD Content Detection

Status: Detector module implemented; OpenClaw runtime requires detector

This module will house ClawGuard detection rules for adversarial or unsafe job-description content observed through the OpenClaw `job-search-custom` pipeline.

Detector implementation:

```text
detections/asi06_jd_content/detector.py
```

OpenClaw runtime integration lives in:

```text
target-agent/skills/job-search-custom/job_search_secure.py
```

The OpenClaw runtime imports this detector directly. The previous inline implementation was removed after VPS cron confirmed the detector-backed path on 2026-05-04.

## Planned Rules

| Rule | Name | Status |
|---|---|---|
| ASI06-001 | Job Description Prompt Injection | Implemented in detector |
| ASI06-002 | Job Description PII Request | Implemented in detector |
| ASI06-003 | Job Description Skill Stuffing | Implemented in detector |
| ASI06-004 | Suspicious Apply Domain | Implemented in detector; ClawGuard-original rule |

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

Package `job_search_secure.py` and `detections/` together for the next VPS deployment. Three clean sessions have landed, so ASI01 is now scaffolded separately while ASI06 has the first importable detection engine module.
