# Target Agent: OpenClaw Deployment

This directory documents the live OpenClaw deployment that ClawGuard monitors. The target runs on a dedicated VPS and produces real telemetry for security monitoring.

## Deployment Overview

| Component | Detail |
|---|---|
| Platform | OpenClaw |
| Hosting | Hostinger KVM 2 |
| Runtime | Docker container behind Traefik |
| Interface | Telegram bot |
| OS | Ubuntu 24.04 |
| Primary monitored skill | `job-search-custom` |
| Container | `openclaw-utxu-openclaw-1` |

## Active Use Case

### Job Search Maintenance Pipeline

The active target is the `job-search-custom` skill. It searches a minimal source set, stores job records in SQLite, scores jobs against the local profile, and produces ClawGuard telemetry after digest compilation.

Current maintenance schedule:

```text
9:00 AM PT  LinkedIn
9:10 AM PT  CyberSecJobs
9:20 AM PT  USAJobs
9:30 AM PT  Compile digest and emit ClawGuard telemetry
```

Current controls:

- Human-in-the-loop remains required for any application submission.
- Cron compile uses `--no-prepare`.
- JD enrichment is disabled with `CLAWGUARD_ENRICHMENT_DAILY_CAP=0`.
- Oxylabs is disabled with `CLAWGUARD_DISABLE_OXYLABS=1`.
- Brave Search and USAJobs native API provide zero-credit maintenance collection.

## Planned Or Secondary Use Cases

The original OpenClaw target model includes:

- Networking or relationship manager.
- Threat-intel morning brief.

Those remain useful future telemetry sources, but the current ClawGuard integration work is centered on the job-search pipeline.

## Skill Security Policy

No community skills are installed without source code review. All skills in `skills/` are custom-written or audited line by line before deployment. This is a deliberate guardrails-first decision based on the OpenClaw skill supply-chain risk documented in `lessons/`.

## OWASP Threat Mapping

| Use Case | OWASP Risk | Attack Vector |
|---|---|---|
| Job search | ASI01 Goal Hijack | Malicious job content redirects agent behavior |
| Job search | ASI02 Tool Misuse | Agent uses tools beyond intended scope |
| Job search | ASI06 Memory Poisoning | Adversarial job content affects context, scoring, or generated materials |
| Skill supply chain | ASI03 Identity and Privilege Abuse | Malicious skill reads secrets or exfiltrates files |
| Browser/search ingestion | ASI05 Unexpected Code Execution | Unsafe browser or scraper behavior expands runtime risk |

## Directory Structure

```text
target-agent/
  docs/      Attack surface mapping and verification logs
  skills/    Custom or audited skills only
  README.md  This file
```

## Current ClawGuard Signal

The first baseline session, `digest-20260502T143953-c9eb7f4c`, evaluated 22 jobs with 0 ASI06 findings and 0 Oxylabs credits. That clean run is documented in `lessons/clawguard-telemetry-baseline-001.md`.
