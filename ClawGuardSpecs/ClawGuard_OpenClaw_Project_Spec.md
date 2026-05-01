# ClawGuard + OpenClaw Project Spec
## Brainstorm Session — March 23, 2026

---

## PROJECT OVERVIEW

**ClawGuard** is a guardrail-first AI agent security monitoring framework that detects OWASP Agentic Top 10 threats against AI agents. It uses a live **OpenClaw** deployment as its real-world test target.

**Elevator pitch:** "I deployed a real AI agent platform, mapped its attack surface, and built an open-source security monitoring framework that detects OWASP Agentic Top 10 violations in real agent behavior — the EDR/SIEM equivalent for the agent era."

---

## REPO STRUCTURE (Option B — Single Repo)

```
clawguard/
├── target-agent/              # OpenClaw deployment
│   ├── README.md              # Setup guide, architecture notes
│   ├── docker-compose.yml     # Config (sanitized, no secrets)
│   ├── skills/                # Custom skills you build
│   └── docs/                  # Attack surface mapping
├── detections/                # ClawGuard detection modules
├── lessons/                   # Teaching docs (differentiator)
│   └── bot-detection-agent-monitoring.md  # First entry planned
└── README.md                  # Project overview
```

---

## OPENCLAW DEPLOYMENT

### Hosting: Hostinger KVM 2
- **Specs:** 2 vCPU, 8GB RAM, 100GB NVMe, 8TB bandwidth
- **Cost:** $9.99/mo (12-month plan), renews at $16.99/mo
- **Location:** United States (closest to Seattle)
- **Add-ons to BUY:** OpenClaw auto-deploy + nexos.ai credits ($5.99), Oxylabs 1000 credits (FREE)
- **Add-ons to SKIP:** Dedicated AI email ($0.45/mo), Daily auto-backup ($6.00/mo)
- **Total upfront:** ~$125.87

### LLM Backend
- **Phase 1:** API-based (own API keys — OpenAI or Anthropic)
- **Phase 2 (optional):** Ollama + Llama 3.x local (would need KVM 4 upgrade for 16GB RAM)
- nexos.ai credits included for initial testing, switch to own keys after

### Messaging Interface
- **Telegram** — primary interface for alerts, digests, agent interaction

---

## THREE USE CASES

### Use Case 1: Job Hunting Agent (PRIMARY) 🎯

**Purpose:** Search job boards, score JDs against resume, tailor resume/cover letters, log everything.

**Target Sites:** LinkedIn, Indeed, Monster, Dice, Glassdoor, ZipRecruiter, Google Jobs

**Target Roles (keywords):**
- SOC Analyst II / III
- SOC Engineer (early career)
- Security Engineer
- Customer Success Engineer
- Threat Hunter (Junior)
- AI Security Engineer
- Detection Engineer
- Security Operations Engineer

**OpenClaw Skills:**
- `job-auto-apply` — LinkedIn, Indeed, Glassdoor, ZipRecruiter, Wellfound (use in dry_run/require_confirmation mode)
- `job-search-mcp` — JobSpy cross-platform search (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs, Monster)

**Workflow:**
1. Search agent scans job boards for matching roles
2. Matching agent scores each JD against master resume (% fit)
3. Tailoring agent adjusts resume bullets + generates cover letter (70%+ matches)
4. Tracking agent logs: JD, company, date, match score, resume version, cover letter, status
5. Alerting agent sends Telegram daily digest
6. **HUMAN clicks submit** (v1 = find + prepare, not auto-submit)

**Data touched (ClawGuard relevance):** Resume, personal contact info, job history, skills, salary expectations, outbound web requests to multiple platforms.

**OWASP mapping:**
- ASI01 (Goal Hijack) — malicious JD with prompt injection redirects agent
- ASI02 (Tool Misuse) — agent sends data to unexpected destinations
- ASI06 (Memory Poisoning) — adversarial input corrupts learned job preferences

### Use Case 2: Networking / Relationship Manager 🤝

**Purpose:** Maintain professional relationships during job search.

**Workflow:**
- Maintain contact list of LinkedIn connections, colleagues, mentors
- Configurable schedule (weekly/bi-weekly)
- Generate digest: who to contact, suggested message, recent LinkedIn activity to reference
- **Does NOT auto-send** — prepares drafts and context for you

**ClawGuard relevance:** Accesses social graph — ASI06 (Memory Poisoning) via adversarial content on contact profiles.

### Use Case 3: Threat Intel Morning Brief ☕

**Purpose:** Stay current for interviews, demonstrate ongoing professional engagement.

**Workflow:**
- Daily cron job scans: CISA, BleepingComputer, Krebs, The Hacker News, OWASP feeds
- Summarizes top 5 items relevant to AI security, agentic threats, SOC operations
- Pushes morning brief to Telegram

**ClawGuard relevance:** Ingests external web content — ASI01 (Goal Hijack) via prompt injection in scraped content.

---

## CLAWGUARD ARCHITECTURE (From Previous Sessions)

### Core Thesis
- AI agents are untrusted by default
- The "infinite loop" problem terminates at a human-owned policy layer
- 4-layer accountability: Agent Acts → Monitor Observes → Ruleset Defines "Wrong" → Humans Audit Ruleset
- **Context Ledger** = key innovation (unified context at machine speed)

### 5-Layer Defense-in-Depth
Regex → AST → ShellGuard → LLM → SOC Ledger

### Taint Handshake Protocol
Deterministic + semantic analysis

### 5-Primitive Attack Surface (OpenClaw-specific)

| Primitive | Attack Vector | Detection Coverage |
|---|---|---|
| Agentic Wallet (X402) | Drain via malicious skill | Spending anomaly detection |
| Cloudflare Markdown | Prompt injection at machine speed | Content poisoning detection |
| Shell tool | Arbitrary code execution | Container behavior monitoring |
| Skills (versioned SOPs) | Malicious skill as legitimate | Skill provenance verification |
| Agent search (Exa) | Adversarial content redirection | Search result integrity |

### OWASP Agentic Top 10 Focus (Phase 1)
- **ASI01 — Goal Hijack:** Attacker redirects agent's objective mid-task
- **ASI02 — Tool Misuse:** Agent uses tools beyond intended scope
- **ASI06 — Memory Poisoning:** Adversarial inputs corrupt long-term memory/context

### Detection Stack
- LangGraph (agent framework)
- Ollama + Llama 3.x (local LLM for detection reasoning)
- W&B Weave / Langfuse (observability)
- Streamlit (dashboard)
- Promptfoo / Giskard / Inspect (testing/red-teaming)

---

## BOT DETECTION ↔ AGENT MONITORING (Lessons Entry)

**Planned article:** "What Job Site Bot Detection Teaches Us About AI Agent Security Monitoring"

Job platform anti-bot techniques that map to ClawGuard patterns:
- **Speed detection** → Agent behavioral velocity monitoring
- **Behavioral analysis** (mouse patterns, click timing) → Agent action pattern analysis
- **Browser fingerprinting** → Agent identity/provenance verification
- **Rate limiting / account flagging** → Agent rate anomaly detection
- **CAPTCHA / human verification** → Human-in-the-loop checkpoints

---

## SKILL SECURITY NOTE

OpenClaw's ClawHub has 13,700+ community skills. Since Feb 2026, VirusTotal scanning blocks malicious downloads, but reviewing source code before installing is still recommended.

**ClawGuard opportunity:** Build skill supply chain security scanning (originally called "SkillScan" concept) as a detection module.

---

## FORWARD ACTION TRACKER

| # | Action | Status | Notes |
|---|--------|--------|-------|
| ✅ 1 | Define OpenClaw use cases | DONE | 3 use cases specced |
| ✅ 2 | Choose Hostinger plan | DONE | KVM 2, $9.99/mo, 12mo |
| 🔲 3 | Create ClawGuard repo with target-agent/ structure | NEXT | Scaffold before deploying |
| 🔲 4 | Purchase Hostinger & deploy OpenClaw | PENDING #3 | Skip email + daily backup add-ons |
| 🔲 5 | Configure job hunting agent (Use Case 1) | PENDING #4 | Install skills, set up profile, test dry run |
| 🔲 6 | Recon environment & document attack surface | PENDING #5 | SSH in, map secrets/ports/APIs/skills |
| 🔲 7 | Bring recon notes → design first ClawGuard detection | PENDING #6 | Map to OWASP ASI codes |
| 🔲 8 | Write first lessons/ entry (bot detection) | ONGOING | Collecting material as we build |

---

## KEY DECISIONS MADE

1. **Option B approved** — OpenClaw lives inside ClawGuard repo under `target-agent/`
2. **AgentWatch folded into ClawGuard** as Phase 1 (detection engine)
3. **No auto-submit in v1** — human-in-the-loop for job applications
4. **API-based LLM first** — own keys, not running local models on VPS
5. **Lever is an ATS, not a job site** — targeting LinkedIn, Indeed, Monster, Dice, Glassdoor, ZipRecruiter
6. **UT Austin AI/ML program completed** ~6 months ago (Sep/Oct 2025)
7. **Guardrails-first design** remains the philosophical anchor across all projects
