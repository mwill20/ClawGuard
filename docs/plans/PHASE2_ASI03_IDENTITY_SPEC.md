# Phase 2 - ASI03 Identity and Privilege Abuse Roadmap

Last updated: 2026-05-05
Status: Roadmap spec only; no runtime detector in Phase 2
Predecessors: ASI06, ASI01, ASI02 detector-backed telemetry

## Purpose

ASI03 covers identity and privilege abuse: credential theft, token misuse,
unexpected identity switching, and unauthorized access expansion. In the current
OpenClaw target, this risk exists around `.env` secrets, API keys, gateway
tokens, messaging credentials, and any future agent identity tokens.

This spec intentionally does not create a regex-only runtime detector. ASI03
needs identity-use telemetry before findings can be reliable.

## Current Project Implements

- Private profile separation through `CLAWGUARD_PROFILE_PATH`.
- `.env` kept out of Git.
- Preflight guard for tracked private profile strings.
- Telemetry redaction for email, phone, deployment identifiers, profile strings,
  and configurable patterns.
- Historical attack-surface notes documenting token reuse and plaintext secret
  risks.

## Threat Model

Untrusted content or compromised tooling attempts to:

- Read API keys, bot tokens, gateway tokens, or profile files.
- Reuse one token across multiple contexts.
- Send credentials to an external destination.
- Switch from the intended user/service identity to a more privileged identity.
- Trigger hidden authentication flows or OAuth consent prompts.

## Required Runtime Signals Before Implementation

Do not implement ASI03 runtime rules until the minimum contract in
[PHASE2_RUNTIME_TELEMETRY_CONTRACT.md](PHASE2_RUNTIME_TELEMETRY_CONTRACT.md)
is available from runtime instrumentation.

At minimum, ASI03 needs:

| Signal | Why It Matters |
|---|---|
| Identity context events | Shows which user/service identity was active for the session |
| Credential-use events | Shows when a key/token is read or used |
| File-access or network-egress events | Shows where identity material may have been read from or sent |
| Policy decisions | Shows whether the action was allowed, blocked, observed, or routed to review |
| Session correlation | Maps every event back to `agent_session_id` |

## Candidate Rule Families

| Future rule_id | Trigger | Required evidence |
|---|---|---|
| `ASI03_SECRET_FILE_ACCESS` | Agent/tool reads a configured secret path unexpectedly | path, tool, caller, session, policy decision |
| `ASI03_TOKEN_EXFIL_ATTEMPT` | Credential-like material sent to external destination | destination, redacted sample hash, source path, session |
| `ASI03_IDENTITY_CONTEXT_SWITCH` | Agent changes auth context outside approved workflow | old identity, new identity, tool, reason, session |
| `ASI03_SCOPE_ESCALATION` | Agent requests broader permission than task requires | requested scope, allowed scope, tool, session |

## Non-Goals

- Do not scan arbitrary text for words like "token" and call that ASI03.
- Do not persist raw secrets in findings.
- Do not build a runtime ASI03 detector until structured identity/tool telemetry
  exists.

## Phase 2 Deliverables

- Keep this spec linked from `PHASE2_INDEX.md`.
- Keep the runtime-event contract linked from `PHASE2_INDEX.md`.
- Ensure redaction prevents identity artifacts from entering curated telemetry.
- Add ASI03 examples to future red-team labs only as sanitized synthetic records.

## Phase 3 Readiness Checklist

- Tool-call/runtime logging captures identity context, credential labels, file reads, and network sends.
- Sensitive path allowlist/denylist exists.
- Findings can store redacted hashes or labels without leaking secret values.
- Deployment config snapshots can prove expected identity context.
- A curated false-positive set exists for security-role job descriptions that
  mention secrets defensively.
