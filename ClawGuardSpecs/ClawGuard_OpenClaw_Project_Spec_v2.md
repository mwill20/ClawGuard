# ClawGuard + OpenClaw Project Spec (v2)
## Updated: March 23, 2026 — Post-Deployment

---

## PROJECT OVERVIEW

**ClawGuard** is a guardrail-first AI agent security monitoring framework that detects OWASP Agentic Top 10 threats against AI agents. It uses a live **OpenClaw** deployment as its real-world test target.

**Elevator pitch:** "I deployed a real AI agent platform, mapped its attack surface, and built an open-source security monitoring framework that detects OWASP Agentic Top 10 violations in real agent behavior — the EDR/SIEM equivalent for the agent era."

---

## REPO STRUCTURE (Option B — Single Repo, Approved)

```
clawguard/
├── .gitignore
├── LICENSE                        # MIT
├── README.md                      # Project overview with elevator pitch
├── target-agent/                  # OpenClaw deployment
│   ├── README.md                  # Deployment guide + OWASP mapping
│   ├── docs/
│   │   └── attack-surface-recon.md  # 8 recon findings
│   └── skills/
│       └── README.md              # Custom skill security policy
├── detections/                    # ClawGuard detection modules
│   └── README.md                  # Detection development guide
└── lessons/                       # Teaching docs (differentiator)
    └── README.md                  # Planned articles + previews
```

**Repo:** https://github.com/mwill20/ClawGuard (currently empty — scaffold files ready to push)

**Scaffold zip:** Available from Claude chat. Extract to local project dir, then git init + push.

---

## OPENCLAW DEPLOYMENT (LIVE ✅)

### Hosting: Hostinger KVM 2
- **VPS IP:** 31.97.139.139
- **Hostname:** srv1523277
- **OS:** Ubuntu 24.04.4 LTS
- **Specs:** 2 vCPU, 8GB RAM, 100GB NVMe, 8TB bandwidth
- **Cost:** $9.99/mo (12-month plan)

### Deployment Architecture
- **OpenClaw version:** 2026.3.12 (build 6472949)
- **Container:** `ghcr.io/hostinger/hvps-openclaw:latest` (Docker)
- **Container name:** `openclaw-utxu-openclaw-1`
- **Reverse proxy:** Traefik (TLS via Let's Encrypt)
- **Gateway port:** 42822
- **LLM:** `google/gemini-2.5-flash`
- **Interface:** Telegram bot (`@clawgaurd_agent_bot`)
- **DM policy:** allowlist (Telegram ID 8778037036)
- **Disabled plugins:** WhatsApp, Discord, Slack, Nostr, Google Chat
- **Credentials:** ALL ROTATED ✅

### File System (On Host)
- **Config:** `/docker/openclaw-utxu/data/.openclaw/openclaw.json`
- **Auth:** `/docker/openclaw-utxu/data/.openclaw/agents/main/agent/auth-profiles.json`
- **Env:** `/docker/openclaw-utxu/.env`
- **Docker Compose:** `/docker/openclaw-utxu/docker-compose.yml`
- **Workspace:** `/docker/openclaw-utxu/data/.openclaw/workspace/`

### Useful Commands
```bash
ssh root@31.97.139.139
docker ps
docker logs openclaw-utxu-openclaw-1 --tail 30
docker restart openclaw-utxu-openclaw-1
nano /docker/openclaw-utxu/data/.openclaw/openclaw.json
docker exec -it openclaw-utxu-openclaw-1 openclaw config set agents.defaults.model "google/gemini-2.5-flash"
```

---

## ATTACK SURFACE FINDINGS (8 Total)

1. **Gateway Token Reuse (MED)** — Same token for hooks, gateway auth, remote access. ASI03.
2. **Unrestricted Bash Access (HIGH)** — `"bash": true`, agent can exec arbitrary commands. ASI01/ASI02.
3. **Browser Sandbox Disabled (MED)** — `"noSandbox": true`. ASI05.
4. **Excessive Plugins (LOW)** — 6 enabled, only 1 needed. RESOLVED: disabled all but Telegram.
5. **Port 42822 Public (MED)** — Bound to 0.0.0.0.
6. **Secrets in Plaintext (MED)** — API keys in .env and openclaw.json. ASI03.
7. **WhatsApp Health Loop (LOW)** — Restarting every 10min. RESOLVED: disabled.
8. **Skill Supply Chain (MED)** — 13,700+ community skills, ClawHavoc attack Feb 2026. RESOLVED: custom skills only.

---

## SKILL AUDIT RESULTS

**`job-auto-apply`** (by veeky-kumar): Reviewed SKILL.md and job_search_apply.py. The Python code is placeholder scaffold — `search_jobs()` returns an empty list with a comment "this is a placeholder." No real functionality. No malicious code found, but also nothing useful.

**`job-search-mcp`** (by chinpeerapat): 404 at documented GitHub path. Doesn't exist where listed.

**Decision:** Write custom skills from scratch. Audited, lean, documented.

---

## FORWARD ACTION TRACKER

| # | Action | Status | Notes |
|---|--------|--------|-------|
| ✅ 1 | Define OpenClaw use cases | DONE | 3 use cases specced |
| ✅ 2 | Choose Hostinger plan | DONE | KVM 2, $9.99/mo |
| ✅ 3 | Deploy OpenClaw | DONE | Live, gemini-2.5-flash, Telegram working |
| ✅ 4 | Rotate credentials | DONE | All rotated |
| ✅ 5 | Disable unused plugins | DONE | Only Telegram active |
| ✅ 6 | Recon & document attack surface | DONE | 8 findings |
| ✅ 7 | Audit community skills | DONE | Both unusable, writing custom |
| 🔲 8 | Clean up accidental .git | NEXT | VPS: `rm -rf /root/.git` + Windows: `Remove-Item -Force C:\Users\20mdw\.git -Recurse` |
| 🔲 9 | Push repo scaffold to GitHub | NEXT | Extract zip → cd into dir → git init/push |
| 🔲 10 | Write custom job search skill | BUILD | Lean SKILL.md: find+score+prep, no auto-submit |
| 🔲 11 | Configure job hunting agent | PENDING #10 | Profile, resume, search params, test via Telegram |
| 🔲 12 | Design first ClawGuard detection | PENDING #11 | ASI01 goal hijack against real agent telemetry |
| 🔲 13 | Write lessons/ entries | ONGOING | Bot detection + skill supply chain articles |

---

## KEY DECISIONS

1. **Option B** — OpenClaw inside ClawGuard repo under `target-agent/`
2. **AgentWatch folded into ClawGuard** as Phase 1
3. **No auto-submit v1** — human-in-the-loop
4. **API-based LLM** — gemini-2.5-flash (cost-optimized)
5. **Telegram allowlist** over pairing
6. **Custom skills only** — no community installs without source audit
7. **Guardrails-first** — security is the architecture, not an afterthought

---

## HANDOVER: NEXT SESSION PRIORITIES

### Immediate cleanup:
1. `Remove-Item -Force C:\Users\20mdw\.git -Recurse` (Windows)
2. `ssh root@31.97.139.139` → `rm -rf /root/.git` (VPS)
3. Extract scaffold zip → push to https://github.com/mwill20/ClawGuard

### Then build:
1. Write custom job search OpenClaw skill (SKILL.md)
2. Configure job hunting agent with profile + resume
3. Design first ClawGuard detection (ASI01)
4. Write lessons/ entries
