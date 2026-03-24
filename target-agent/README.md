# Target Agent — OpenClaw Deployment

This directory documents the live OpenClaw deployment that ClawGuard monitors. The agent runs on a dedicated VPS and handles real automation tasks, generating authentic telemetry for security monitoring.

## Deployment Overview

| Component | Detail |
|---|---|
| Platform | OpenClaw 2026.3.12 |
| Hosting | Hostinger KVM 2 (2 vCPU, 8GB RAM, 100GB NVMe) |
| Runtime | Docker container with Traefik reverse proxy |
| LLM Backend | Google Gemini 2.5 Flash (API-based, cost-optimized) |
| Interface | Telegram bot |
| OS | Ubuntu 24.04.4 LTS |

## Use Cases

### 1. Job Hunting Agent (Primary)
Searches LinkedIn, Indeed, Monster, Dice, Glassdoor, ZipRecruiter for matching roles. Scores JDs against master resume, tailors resume bullets and cover letters for high-match positions. **Human-in-the-loop for final submission** — the agent finds and prepares, you click apply.

### 2. Networking / Relationship Manager
Maintains contact list of LinkedIn connections, colleagues, and mentors. Generates weekly digest of who to reach out to with suggested messages and recent activity context. Does NOT auto-send messages.

### 3. Threat Intel Morning Brief
Daily scan of CISA, BleepingComputer, Krebs on Security, The Hacker News, and OWASP feeds. Summarizes top 5 items relevant to AI security and SOC operations. Pushes morning brief to Telegram.

## Skill Security Policy

**No community skills are installed without source code review.** All skills in the `skills/` directory are custom-written or audited line-by-line before deployment. This is a deliberate guardrails-first decision — see `lessons/` for documentation on OpenClaw skill supply chain risks.

## OWASP Threat Mapping

| Use Case | OWASP Risk | Attack Vector |
|---|---|---|
| Job Hunting | ASI01 (Goal Hijack) | Malicious JD with prompt injection redirects agent behavior |
| Job Hunting | ASI02 (Tool Misuse) | Agent sends resume/PII to unexpected destinations |
| Job Hunting | ASI06 (Memory Poisoning) | Adversarial input corrupts learned job preferences |
| Networking | ASI06 (Memory Poisoning) | Adversarial content on contact profiles poisons agent memory |
| Threat Intel | ASI01 (Goal Hijack) | Prompt injection embedded in scraped news content |

## Directory Structure

```
target-agent/
├── docs/                  # Attack surface mapping & recon findings
├── skills/                # Custom-built, audited skills only
└── README.md              # This file
```

## Configuration Notes

See `docs/` for detailed attack surface findings and hardening recommendations.
