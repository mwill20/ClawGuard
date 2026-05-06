# Phase 2 - ASI05 Unexpected Code Execution Roadmap

Last updated: 2026-05-05
Status: Roadmap spec only; no runtime detector in Phase 2
Predecessors: ASI02 tool-misuse detector and deploy/cron telemetry

## Purpose

ASI05 covers unexpected code execution: the agent or its tools run code,
commands, scripts, browser automation, or container operations outside the
intended task boundary.

ASI02 v1 already detects untrusted content that tries to drive shell payloads.
ASI05 requires runtime process or tool-call telemetry to prove execution
actually occurred or was attempted.

## Current Project Implements

- ASI02 content-side shell payload detection.
- Human approval before any application submission.
- Deploy helper syntax-checks the OpenClaw runtime and detector modules before
  remote activation.
- Preflight parses Python files and runs fixture evaluations.
- Cron maintenance uses a small, predictable set of commands.

## Threat Model

Untrusted content or compromised tooling attempts to:

- Execute shell commands through templated content.
- Run Python, PowerShell, Bash, or Node snippets unexpectedly.
- Modify cron, deployment helpers, or container state.
- Launch browser or network tooling outside the approved search workflow.
- Chain tool misuse into persistent runtime modification.

## Required Runtime Signals Before Implementation

Do not implement ASI05 runtime rules until the minimum contract in
[PHASE2_RUNTIME_TELEMETRY_CONTRACT.md](PHASE2_RUNTIME_TELEMETRY_CONTRACT.md)
is available from runtime instrumentation.

At minimum, ASI05 needs:

| Signal | Why It Matters |
|---|---|
| Process execution logs | Shows command, args, cwd, exit code, and caller |
| Container-action or file-write logs | Shows Docker exec/cp/restart or mutation operations |
| Policy decisions | Shows whether execution was allowed, blocked, observed, or reviewed |
| Session correlation | Maps every event back to `agent_session_id` |
| Redacted labels | Keeps command args, paths, hosts, and container identifiers out of public artifacts |

## Candidate Rule Families

| Future rule_id | Trigger | Required evidence |
|---|---|---|
| `ASI05_UNEXPECTED_SHELL_EXEC` | Shell command runs outside approved workflow | command, args, cwd, caller, session |
| `ASI05_SCRIPT_EXEC_FROM_UNTRUSTED_CONTENT` | Script content derived from job text is executed | source field, script hash, tool, session |
| `ASI05_CONTAINER_CONTROL_MISUSE` | Unexpected Docker exec/cp/restart action | container, command, actor, session |
| `ASI05_CRON_MODIFICATION` | Agent modifies cron outside deployment workflow | file path, diff summary, actor, session |

## Non-Goals

- Do not treat every mention of Bash, Python, curl, malware, or scripts as ASI05.
- Do not duplicate ASI02 content-side shell detection.
- Do not ship runtime blocking until the project has reliable process telemetry
  and a false-positive review set.

## Phase 2 Deliverables

- Keep this spec linked from `PHASE2_INDEX.md`.
- Preserve ASI02 shell payload evidence as the pre-action precursor signal.
- Keep the runtime-event contract linked from `PHASE2_INDEX.md`.
- Validate synthetic runtime-event fixtures before Phase 3.

## Phase 3 Readiness Checklist

- Runtime emits structured process, container, file-write, and policy events.
- Approved command inventory exists for cron, deploy, validation, and local tests.
- Findings can correlate execution events to `agent_session_id`.
- Redaction covers command arguments that may include credentials.
- CI or preflight can replay synthetic process telemetry without touching live
  providers or the VPS.
