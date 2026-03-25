# OpenClaw Project Spec

**Version:** v2.1 (Post-Deployment)  
**Status:** Live on VPS, skills in progress  
**Owner:** Michael Williams (ClawGuard)  
**Date:** March 24, 2026

---

## 🎯 NORTH STAR

Deploy and operate a real AI agent platform on a dedicated VPS, generate authentic telemetry, and feed it into ClawGuard's detection engine. OpenClaw is the **target**, not the deliverable — its value is the data it produces for security monitoring.

**Success criteria:**
- ✅ Deployment live (31.97.139.139)
- ✅ Telegram integration working
- 🔲 Custom job-search-custom skill installed and tested
- 🔲 Agent producing real execution traces
- 🔲 Logs feeding into ClawGuard detection pipeline

---

## 📋 CURRENT STATE

### Deployment Status
| Component | Status | Details |
|-----------|--------|---------|
| **VPS** | ✅ LIVE | Hostinger KVM 2, Ubuntu 24.04, 31.97.139.139 |
| **OpenClaw** | ✅ RUNNING | v2026.3.12, Docker container, Traefik reverse proxy |
| **LLM Backend** | ✅ CONFIGURED | google/gemini-2.5-flash (cost-optimized) |
| **Telegram Bot** | ✅ PAIRED | @clawgaurd_agent_bot, user ID 8778037036 |
| **Oxylabs API** | ✅ LIVE | 1000 credits, key in .env, verified working |
| **Credentials** | ✅ ROTATED | All exposed keys regenerated |
| **Messaging** | ✅ HARDENED | Telegram allowlist only, other plugins disabled |

### Architecture
```
┌─────────────────────────────────────────┐
│ VPS (31.97.139.139)                     │
├─────────────────────────────────────────┤
│ Docker Container: openclaw-utxu         │
│ ├─ OpenClaw Gateway (port 42822)        │
│ ├─ Config: /data/.openclaw/             │
│ ├─ Workspace: /data/.openclaw/workspace/│
│ └─ Logs: /docker/openclaw-utxu/         │
├─────────────────────────────────────────┤
│ Traefik Reverse Proxy (TLS)             │
│ └─ Domain: openclaw-utxu.srv1523277...  │
├─────────────────────────────────────────┤
│ Telegram Bot Interface                  │
│ └─ DM Policy: allowlist (user 8778...)  │
└─────────────────────────────────────────┘
```

### File System (On Host)
```
/docker/openclaw-utxu/
├── .env                              # Secrets (Oxylabs key, bot token, etc.)
├── docker-compose.yml                # Container config
└── data/
    └── .openclaw/
        ├── openclaw.json             # Main config
        ├── openclaw.json.bak         # Auto-backup
        ├── agents/main/
        │   ├── agent/auth-profiles.json  # API keys
        │   └── sessions/              # Execution history
        ├── workspace/                 # Agent working directory
        ├── cron/jobs.json             # Scheduled tasks
        ├── credentials/               # Restricted perms
        ├── logs/                      # Execution logs (restricted)
        └── extensions/                # Custom skills directory
```

### Useful Commands
```bash
# SSH in
ssh root@31.97.139.139

# Check container status
docker ps | grep openclaw

# View logs (last 30 lines)
docker logs openclaw-utxu-openclaw-1 --tail 30 -f

# Restart after config changes
docker restart openclaw-utxu-openclaw-1

# Edit main config
nano /docker/openclaw-utxu/data/.openclaw/openclaw.json

# Set model via CLI
docker exec -it openclaw-utxu-openclaw-1 openclaw config set agents.defaults.model "google/gemini-2.5-flash"

# Agent management
docker exec -it openclaw-utxu-openclaw-1 openclaw agents list
docker exec -it openclaw-utxu-openclaw-1 openclaw agents add main
```

---

## 📦 DELIVERABLES (PHASED)

### Phase 1: Skills Setup (THIS WEEK)
**Goal:** Install custom job-search-custom skill, test end-to-end via Telegram.

| Deliverable | Status | Owner | Notes |
|-------------|--------|-------|-------|
| `job-search-custom/SKILL.md` | ✅ READY | Claude | In outputs folder, ready to deploy |
| `job-search-custom/AUDIT.md` | ✅ READY | Claude | Vulnerability analysis vs. original |
| `job-search-custom/job_search_secure.py` | ✅ READY | Claude | Implementation (demo mode, ready for Oxylabs integration) |
| Move files to repo | 🔲 PENDING | You | Copy into `target-agent/skills/job-search-custom/` |
| Push to GitHub | 🔲 PENDING | You | `git add/commit/push` |
| SSH install skill | 🔲 PENDING | You | Copy to `/docker/openclaw-utxu/data/.openclaw/extensions/job-search-custom/` |
| Docker restart | 🔲 PENDING | You | `docker restart openclaw-utxu-openclaw-1` |
| Telegram test | 🔲 PENDING | You | Send: "Search for SOC Analyst jobs in Remote" |
| Document test results | 🔲 PENDING | You | Log output in `target-agent/docs/skill-test-log.md` |

### Phase 2: Agent Configuration (NEXT WEEK)
**Goal:** Configure job hunting agent with profile, search parameters, and scheduling.

| Deliverable | Status | Owner | Notes |
|-------------|--------|-------|-------|
| Job search profile (JSON) | 🔲 TODO | You | Resume, target roles, location prefs |
| Search parameters | 🔲 TODO | You | Keywords, salary range, job types |
| Schedule cron job | 🔲 TODO | You | Daily 9am job search, Telegram digest |
| Test dry-run | 🔲 TODO | You | Generate sample prepared materials |
| Document workflow | 🔲 TODO | You | Add to `target-agent/docs/` |

### Phase 3: Threat Modeling & Hardening (CONCURRENT)
**Goal:** Identify real attack surface, document findings, harden config.

| Deliverable | Status | Owner | Notes |
|-------------|--------|-------|-------|
| Threat model diagram | 🔲 TODO | Claude | STRIDE or kill-chain for OpenClaw + ClawGuard |
| Attack surface mapping | ✅ DONE | Claude | `target-agent/docs/attack-surface-recon.md` (8 findings) |
| Hardening checklist | 🔲 TODO | Claude | Based on threat model + findings |
| Security runbook | 🔲 TODO | Claude | Incident response for detected threats |
| Lessons entry | 🔲 TODO | Claude | "Skill Supply Chain Security" article |

---

## 🔗 GITHUB SETUP

**Repository:** https://github.com/mwill20/ClawGuard  
**Branch:** main  
**Visibility:** Public (portfolio project)

### Current Structure
```
clawguard/
├── README.md                          # Main project overview + elevator pitch
├── LICENSE                            # MIT
├── .gitignore                         # Secrets, build artifacts
├── target-agent/
│   ├── README.md                      # Deployment guide, use cases, OWASP mapping
│   ├── docs/
│   │   ├── attack-surface-recon.md    # 8 findings from initial recon
│   │   └── skill-test-log.md          # (PENDING) Test results from Telegram
│   └── skills/
│       └── job-search-custom/
│           ├── SKILL.md               # (PENDING) Upload from outputs
│           ├── AUDIT.md               # (PENDING) Upload from outputs
│           └── job_search_secure.py   # (PENDING) Upload from outputs
├── detections/
│   └── README.md                      # Detection module stubs (ASI01, ASI02, ASI06)
└── lessons/
    └── README.md                      # Planned articles + previews
```

### Git Workflow for Claude Code

**Step 1: Clone & set up**
```bash
git clone https://github.com/mwill20/ClawGuard.git
cd ClawGuard
```

**Step 2: Create feature branch**
```bash
git checkout -b feat/job-search-custom-deployment
```

**Step 3: Add skill files**
```bash
# Copy from downloads or outputs folder
cp ~/Downloads/job-search-custom-SKILL.md target-agent/skills/job-search-custom/SKILL.md
cp ~/Downloads/AUDIT.md target-agent/skills/job-search-custom/AUDIT.md
cp ~/Downloads/job_search_secure.py target-agent/skills/job-search-custom/job_search_secure.py
```

**Step 4: Commit & push**
```bash
git add target-agent/skills/job-search-custom/
git commit -m "Add job-search-custom skill: secure, audited job search with Oxylabs + FireCrawl fallback

- SKILL.md: Complete skill documentation and usage guide
- AUDIT.md: Vulnerability analysis vs. original job-auto-apply
- job_search_secure.py: Clean implementation with rate limiting, audit logging, no auto-submit
- Fixes ASI01 (Goal Hijack), ASI02 (Tool Misuse), ASI03 (Identity Abuse) attack vectors
- Replaces broken community skill with transparent, guardrails-first alternative"
git push origin feat/job-search-custom-deployment
```

**Step 5: Create Pull Request**
- Title: "Add secure job-search-custom skill for OpenClaw deployment"
- Description: Link to AUDIT.md for vulnerability analysis
- Review checklist: 
  - [ ] Audit log messages verified
  - [ ] No hardcoded API calls to unexpected endpoints
  - [ ] Human approval gates in place for submission
  - [ ] Rate limiting enforced
  - [ ] Tested via Telegram on VPS

---

## 🛡️ THREAT MODEL (PRELIMINARY)

**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)

### High-Risk Attack Vectors (From Recon)

| Risk | STRIDE | Current Status | Mitigation |
|------|--------|-----------------|------------|
| **Unrestricted Bash** | Elevation of Privilege | HIGH | Detect via ClawGuard ASI02 (Tool Misuse) |
| **Gateway Token Reuse** | Spoofing | MEDIUM | Monitor for token use from unusual IPs (ASI03) |
| **Resume Exfiltration** | Information Disclosure | HIGH (w/ job-search-custom: LOW) | Resume stays local, only tailored bullets sent (job-search-custom) |
| **Prompt Injection in JD** | Tampering | MEDIUM | Treat JD as DATA, extract only structured fields (job-search-custom) |
| **Skill Supply Chain** | Tampering | MEDIUM | Custom skills only, no community installs without audit |
| **Port 42822 Exposed** | Information Disclosure | MEDIUM | Firewall restrict to trusted IPs (future hardening) |
| **Secrets in .env** | Information Disclosure | MEDIUM | File access monitoring (ClawGuard) |

### Threat Model Diagram
**Status:** Pending. To be created after Phase 1 testing. Will show:
- Attack entry points (Telegram, web crawler, malicious job posting)
- Agent decision points (search → score → prepare → submit)
- ClawGuard monitoring checkpoints (each stage)
- Data flow for sensitive fields (resume, contact, credentials)

**Will inform:**
- Priority detection rules (ASI01, ASI02, ASI06 focus)
- Logging strategy (what to capture for forensics)
- Incident response procedures

---

## 📊 MONITORING & OBSERVABILITY

### Logs to Collect
- **Container logs:** `docker logs openclaw-utxu-openclaw-1`
- **Audit log:** `/docker/openclaw-utxu/data/.openclaw/logs/` (restricted perms, SSH only)
- **Skill logs:** `job_search_audit.log` (generated by job-search-custom)
- **Opportunity tracker:** `opportunities_log.json` (generated by job-search-custom)

### Metrics to Track
- Oxylabs API calls (quota usage)
- Search query volume (detect bot behavior)
- Job board requests (rate limiting check)
- Prepared materials generated (human approval rate)
- Actual submissions (should be ZERO until manual submission gates)

### Success Indicators for Phase 1
- ✅ Skill installs without errors
- ✅ `search` command returns jobs via Oxylabs OR FireCrawl fallback
- ✅ `score` command ranks jobs by match score
- ✅ `prepare` command generates cover letter draft + checklist
- ✅ Human approval gates prevent auto-submit
- ✅ All API calls logged and auditable
- ✅ No unexpected network connections detected

---

## 🚀 NEXT IMMEDIATE ACTIONS (Priority Order)

### For You (OpenClaw Operator)
1. **Download skill files** from Claude outputs folder
2. **Create directory:** `C:\Projects\ClawGuard\target-agent\skills\job-search-custom\`
3. **Move 3 files** into that directory (SKILL.md, AUDIT.md, job_search_secure.py)
4. **Push to GitHub:**
   ```powershell
   cd C:\Projects\ClawGuard
   git add target-agent/skills/job-search-custom/
   git commit -m "Add job-search-custom skill"
   git push
   ```
5. **SSH to VPS** and install:
   ```bash
   ssh root@31.97.139.139
   # Copy skill to OpenClaw
   cp -r /path/to/job-search-custom /docker/openclaw-utxu/data/.openclaw/extensions/
   # Restart OpenClaw
   docker restart openclaw-utxu-openclaw-1
   ```
6. **Test via Telegram:** Send message `Search for SOC Analyst jobs in Remote`
7. **Document results** in `target-agent/docs/skill-test-log.md`

### For Claude Code (Parallel Work)
- [ ] Build threat model diagram (wait for Phase 1 test results)
- [ ] Draft security runbook
- [ ] Write "Skill Supply Chain Security" lessons entry

---

## 📖 HOW CLAUDE CODE SHOULD USE THIS SPEC

**Read this file** when:
- Setting up the deployment workflow
- Understanding data flows and security implications
- Planning threat modeling work
- Building detection rules (reference attack vectors)

**Then:**
1. Ask: *"Based on the OpenClaw threat model and OWASP Agentic Top 10, what are the top 3 ASI codes I should prioritize for ClawGuard detection rules?"*
2. Reference specific attack surfaces: *"The unrestricted bash access (STRIDE: EOP) should be detected by ASI02 (Tool Misuse). How would you design a LangGraph detection rule for this?"*
3. Use deliverables checklist to track progress

---

## 📚 REFERENCE DOCUMENTS

- **OWASP Agentic Top 10 (2026):** https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- **OpenClaw Docs:** https://docs.openclaw.ai
- **Cisco PEAK Threat Hunting Assistant:** Reference architecture for agentic security
- **Job Site Bot Detection Article:** Maps to ClawGuard agent monitoring patterns (lessons entry TBD)

---

## ✅ SIGN-OFF

- **Created:** March 24, 2026
- **Last Updated:** March 24, 2026
- **Next Review:** After Phase 1 skill testing (March 28, 2026)
- **Owner:** Michael Williams
