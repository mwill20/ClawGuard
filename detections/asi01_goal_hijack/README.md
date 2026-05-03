# ASI01 Goal Hijack Detection

Status: Scaffolded from live OpenClaw telemetry

This module will house ClawGuard detection rules for goal redirection attempts against the OpenClaw job-search pipeline and later agent workflows.

The current scaffold is based on three clean OpenClaw telemetry sessions:

| Session | Source | Signal |
|---|---|---|
| `digest-20260502T143953-c9eb7f4c` | Manual maintenance compile | 22 jobs, 0 ASI06 findings |
| `digest-20260502T163002-dbe409f3` | Direct post-compile telemetry verification | 0 findings |
| `digest-20260503T163003-b91b67e1` | First autonomous cron-chain run | 0 new jobs, 0 findings, hook verified |

## Threat Model

Goal hijack occurs when untrusted content or tool output attempts to redirect the agent away from the user's intended objective.

For the current OpenClaw target, the first relevant surface is ingested job content:

```text
User goal:
  Find and score relevant cybersecurity jobs, then prepare materials only when explicitly allowed.

Hijack attempt:
  A job posting, search result, or apply page instructs the agent to change scoring, hide jobs, submit data, contact a third party, or prioritize attacker-controlled instructions.
```

## Initial Rules

| Rule | Name | Status |
|---|---|---|
| ASI01-001 | External Content Goal Redirection | Documented stub |

## Detection Approach

ASI01 is semantic and behavioral first. Regex can identify seed indicators such as "ignore previous instructions" or "do not tell the user," but those strings alone do not prove goal hijack.

The detector needs to compare:

- The user's intended goal.
- The configured agent policy.
- The untrusted external instruction.
- The agent's resulting behavior or proposed action.

This differs from ASI06, where the first useful layer can be direct job-content pattern matching. ASI01 should not become a duplicate regex scanner; it should classify whether unsafe content changed or attempted to change the agent objective.

## Telemetry Inputs

Initial inputs will come from existing OpenClaw job-search telemetry:

- `jobs`
- `job_security_findings`
- `search_runs`
- digest archives under `/data/clawguard/digests/`
- post-compile telemetry summaries under `/data/clawguard/telemetry/`

## Required Evidence Fields

ASI01 findings should preserve:

- `rule_id`
- `severity`
- `message`
- `agent_session_id`
- `job_id` when job-scoped
- source platform or tool name
- source field or tool output field
- matched or summarized redirect instruction
- intended user goal
- observed attempted goal
- recommended human review action

## Relationship To ASI06

ASI06 detects unsafe or adversarial content in the job-description ingestion path. ASI01 should use those ASI06 findings as upstream signals when the content attempts to redirect the agent's objective.

Example:

- ASI06 signal: job description contains "ignore previous instructions."
- ASI01 interpretation: the content attempts to replace the user's job-search objective with attacker-provided instructions.

## Extraction Criteria

Keep this as a documentation scaffold until runtime work is justified by one of these:

- A live posting attempts to redirect scoring, filtering, preparation, or submission behavior.
- ASI06 prompt-injection findings appear and need goal-impact classification.
- A non-job OpenClaw workflow is added as a second telemetry source.
