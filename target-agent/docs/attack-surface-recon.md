# Attack Surface Recon — OpenClaw Deployment

Findings from initial reconnaissance of the OpenClaw deployment on Hostinger KVM 2.

**Date:** March 23, 2026
**Target:** OpenClaw 2026.3.12 (Docker container on Ubuntu 24.04)

---

## Finding 1: Gateway Token Reuse (MEDIUM)

**What:** Same authentication token used across three contexts — hooks, gateway auth, and remote access.

**Risk:** Single point of compromise. If any one context leaks the token, an attacker gains access to all three.

**OWASP mapping:** ASI03 (Identity & Privilege Abuse)

**ClawGuard detection opportunity:** Monitor for token usage from unexpected source IPs or contexts.

---

## Finding 2: Unrestricted Bash Access (HIGH)

**What:** `"bash": true` in the commands configuration with no restrictions — the agent can execute arbitrary shell commands inside the container.

**Risk:** A goal hijack (ASI01) or tool misuse (ASI02) attack could escalate to full container compromise via shell command execution.

**ClawGuard detection opportunity:** Shell command monitoring, command classification against an allowlist, blocklist enforcement for dangerous commands (rm -rf, curl to unknown hosts, etc.).

---

## Finding 3: Browser Sandbox Disabled (MEDIUM)

**What:** `"noSandbox": true` — Chromium browser runs without sandbox isolation.

**Risk:** Any browser-based exploit gets direct container access instead of being contained within the sandbox.

**OWASP mapping:** ASI05 (Unexpected Code Execution)

**ClawGuard detection opportunity:** Monitor browser process behavior, track outbound connections from the browser process.

---

## Finding 4: Excessive Messaging Plugins Enabled (LOW)

**What:** 6 messaging plugins were enabled by default (WhatsApp, Discord, Telegram, Slack, Nostr, Google Chat) when only Telegram is needed.

**Risk:** Each enabled plugin is additional attack surface. WhatsApp health-monitor was consuming resources trying to restart a service that wasn't configured.

**Resolution:** Disabled all plugins except Telegram.

**ClawGuard detection opportunity:** Monitor for unexpected channel activation or messages arriving from disabled channels.

---

## Finding 5: Port 42822 Publicly Exposed (MEDIUM)

**What:** Gateway port bound to `0.0.0.0:42822` — accessible from any IP address on the internet.

**Risk:** Anyone can attempt gateway connections. Token auth provides some protection, but the port shouldn't need to be publicly accessible.

**Mitigation:** Firewall rule to restrict to known IPs, or rely solely on Traefik reverse proxy.

**ClawGuard detection opportunity:** Monitor connection attempts from unknown IPs, alert on connection spikes.

---

## Finding 6: Secrets in Plaintext (MEDIUM)

**What:** API keys, bot tokens, and gateway tokens stored in plaintext in `.env` and `openclaw.json` files.

**Risk:** Any file read vulnerability (or goal hijack that tricks the agent into reading these files) exposes all credentials.

**OWASP mapping:** ASI03 (Identity & Privilege Abuse)

**ClawGuard detection opportunity:** Monitor file access to sensitive paths (`auth-profiles.json`, `.env`, `openclaw.json`).

---

## Finding 7: WhatsApp Health Monitor Loop (LOW/INFO)

**What:** `[health-monitor] [whatsapp:default] health-monitor: restarting (reason: stopped)` — repeating every 10 minutes in the logs.

**Risk:** Log noise could mask real security events. Unnecessary resource consumption.

**Resolution:** Disabled WhatsApp plugin.

---

## Finding 8: Skill Supply Chain Risk (MEDIUM)

**What:** OpenClaw's ClawHub has 13,700+ community skills. The February 2026 ClawHavoc attack poisoned the registry with 1,184 malicious skills including credential stealers and reverse shells.

**Risk:** Installing unreviewed community skills could introduce malicious code with full access to the agent's tools and data.

**Resolution:** All skills are custom-written or audited line-by-line before installation. No blind community skill installs.

**ClawGuard detection opportunity:** Build skill provenance verification and supply chain scanning as a detection module.
