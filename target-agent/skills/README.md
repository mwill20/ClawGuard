# Custom Skills

All skills in this directory are custom-written or audited line by line before deployment.

No community skills from ClawHub are installed without full source code review. This is an explicit ClawGuard supply-chain control, not a convenience choice.

## Active Skill

| Skill | Status | Purpose |
|---|---|---|
| `job-search-custom` | Live | Low-volume OpenClaw job-search pipeline and ClawGuard telemetry source |

## Skill Requirements

Each deployed skill should include:

- `SKILL.md` with OpenClaw-facing instructions.
- Source code or scripts required by the skill.
- `AUDIT.md` documenting reviewed data flows and safety controls.
- Operational runbooks or checklists when the skill has cron or deployment behavior.

## Current Policy

- Resume and contact data stay local.
- Human review is required before any application submission.
- Provider credentials live in VPS `.env`, not in code.
- Brave Search and USAJobs API are allowed maintenance providers.
- Oxylabs is supported but disabled in the active maintenance schedule.
