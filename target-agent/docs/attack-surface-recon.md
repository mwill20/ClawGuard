# Attack Surface Recon - OpenClaw Deployment

Findings from initial reconnaissance of the OpenClaw deployment on Hostinger KVM 2.

Original date: 2026-03-23
Current update: 2026-05-03
Target: OpenClaw Docker deployment on Ubuntu 24.04

## Current Mitigations

The active ClawGuard work focuses on the OpenClaw `job-search-custom` skill as a low-volume telemetry source.

Current controls:

- Community skills are not installed without source review.
- Job-search cron is restricted to LinkedIn, CyberSecJobs, and USAJobs.
- Oxylabs is disabled in maintenance mode.
- Brave Search and USAJobs native API are the active zero-credit providers.
- Application auto-prep is disabled in cron.
- JD enrichment is disabled in cron.
- ASI06 job-content checks persist findings in SQLite.
- Post-compile telemetry summaries are written after successful digest compilation.

The findings below remain the baseline attack-surface map for the target.

## Finding 1: Gateway Token Reuse (MEDIUM)

What: Same authentication token was observed across multiple contexts such as hooks, gateway auth, and remote access.

Risk: A single leaked token can unlock more than one control surface.

OWASP mapping: ASI03 Identity and Privilege Abuse.

ClawGuard detection opportunity: Monitor token usage from unexpected source IPs or contexts.

## Finding 2: Unrestricted Bash Access (HIGH)

What: Bash access is available inside the container.

Risk: A goal hijack or tool misuse attack could escalate into broad container command execution.

OWASP mapping: ASI01 Goal Hijack and ASI02 Tool Misuse.

ClawGuard detection opportunity: Shell command monitoring, command classification, and enforcement around dangerous commands or sensitive file reads.

## Finding 3: Browser Sandbox Disabled (MEDIUM)

What: Browser sandboxing was disabled in the OpenClaw runtime configuration.

Risk: Browser exploit impact may expand into the container.

OWASP mapping: ASI05 Unexpected Code Execution.

ClawGuard detection opportunity: Monitor browser process behavior and outbound connections.

## Finding 4: Excessive Messaging Plugins Enabled (LOW)

What: Multiple messaging plugins were enabled when only Telegram was needed.

Risk: Each enabled plugin expands attack surface and adds log noise.

Resolution: Disable unused messaging plugins.

ClawGuard detection opportunity: Monitor unexpected channel activation or messages from disabled channels.

## Finding 5: Public Gateway Exposure (MEDIUM)

What: The OpenClaw gateway was publicly reachable.

Risk: Token auth helps, but an internet-facing control plane invites probing and brute-force attempts.

Mitigation: Restrict source IPs, route through the intended reverse proxy, or close unnecessary exposure.

ClawGuard detection opportunity: Monitor connection attempts from unknown IPs and alert on spikes.

## Finding 6: Secrets In Plaintext (MEDIUM)

What: API keys, bot tokens, and gateway tokens are stored in `.env` and OpenClaw config files.

Risk: File-read access can expose credentials.

OWASP mapping: ASI03 Identity and Privilege Abuse.

ClawGuard detection opportunity: Monitor file access to sensitive paths such as `.env`, `openclaw.json`, and auth profile files.

## Finding 7: Messaging Health Monitor Noise (LOW)

What: Unused messaging health monitors produced repeated restart logs.

Risk: Noise can hide real operational or security events.

Resolution: Disable unused messaging plugins.

## Finding 8: Skill Supply Chain Risk (MEDIUM)

What: OpenClaw skills are powerful and can access agent tools and local data.

Risk: Installing unreviewed community skills could introduce malicious code, credential theft, or hidden outbound calls.

Resolution: All skills in this repo are custom-written or audited before deployment.

ClawGuard detection opportunity: Build skill provenance verification and supply-chain scanning as a future detection module.

## Current Priority

The highest-value Phase 1 detection surface is ingested job content. The ASI06 rules in `job_search_secure.py` already record prompt-injection, PII-request, skill-stuffing, and apply-domain findings. ASI01 and ASI02 scaffolds should build on the same telemetry discipline after the OpenClaw maintenance baseline has three clean sessions.
