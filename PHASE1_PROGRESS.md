# OpenClaw Phase 1 Progress — Job Hunting Agent

**Last Updated:** 2026-03-25
**Branch:** `feat/job-search-custom-deployment`
**VPS:** `root@31.97.139.139`
**Container:** `openclaw-utxu-openclaw-1`

---

## Quick Start for Next Developer/AI

```bash
# Local repo
cd C:\Projects\ClawGuard
git checkout feat/job-search-custom-deployment

# SSH to VPS
ssh root@31.97.139.139

# Test search (inside container skill dir)
KEY=$(grep "^OXYLABS_AISTUDIO_API_KEY=" /docker/openclaw-utxu/.env | cut -d= -f2)
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 job_search_secure.py search --query "SOC Analyst" --location "Seattle, WA" --max-results 5

# Multi-site search
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 job_search_secure.py search --query "Security Engineer" --location "Seattle, WA" --sites all --budget 30

# Run daily digest
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 job_search_secure.py digest --budget 50 --format telegram

# Check credit quota
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 \
  python3 job_search_secure.py quota

# If you change .env, you MUST recreate (restart does NOT re-read .env):
cd /docker/openclaw-utxu && docker compose down && docker compose up -d
# Then re-install pip package and re-copy skill files:
docker exec openclaw-utxu-openclaw-1 pip install oxylabs-ai-studio --break-system-packages
docker cp /tmp/job_search_secure.py openclaw-utxu-openclaw-1:/usr/local/lib/node_modules/openclaw/skills/job-search-custom/
```

---

## Phase 1 Scope: Job Hunting Agent (Use Case 1 of 3)

### Overall Progress: 100% ✅ (Live in Production)

---

## Checklist

### Infrastructure (COMPLETE)

- [x] VPS deployed (31.97.139.139, Hostinger KVM 2, Ubuntu 24.04)
- [x] OpenClaw container running (`ghcr.io/hostinger/hvps-openclaw:latest`)
- [x] Telegram bot paired (`@clawgaurd_agent_bot`, user ID `8778037036`)
- [x] Oxylabs AI Studio API key configured (40 chars, in `.env`)
- [x] `.env` file cleaned (malformed first line fixed)
- [x] Container recreated with correct env vars (`docker compose down && up`)
- [x] `oxylabs-ai-studio` Python package installed in container
- [x] Git repo initialized, remote set to `github.com/mwill20/ClawGuard`
- [x] SSH key added to VPS (`id_ed25519` for `mwill.itmission@gmail.com`)

### Skill Deployment (COMPLETE)

- [x] Skill files in container: `/usr/local/lib/node_modules/openclaw/skills/job-search-custom/`
- [x] Files: `job_search_secure.py`, `SKILL.md`, `job_search_profile.json`, `resume.txt`
- [x] `TOOLS.md` updated with all commands and profile context
- [x] Agent correctly routes job search requests to skill

### Search (COMPLETE — 8 sites)

- [x] Oxylabs AI Studio SDK integration (real API calls)
- [x] LinkedIn — working (no JS, 1 credit)
- [x] Indeed — working (JS rendering, 4 credits)
- [x] Monster — working (JS rendering, 4 credits)
- [x] Dice — working (JS rendering, 4 credits) — **IT/tech niche**
- [x] CyberSecJobs — working (no JS, 1 credit) — **cybersecurity niche**
- [x] InfoSec Jobs — working (no JS, 1 credit) — **infosec niche**
- [x] SimplyHired — working (JS rendering, 4 credits) — **aggregator**
- [x] USAJobs — working (JS rendering, 4 credits) — **government/cleared**
- [x] Rate limiting (5s between searches, 50 result cap)
- [x] Persistent quota tracking (`oxylabs_quota.json`, auto-resets monthly)
- [x] Multi-site search with deduplication (`search_all_sites()`)
- [x] Combined OR queries for credit efficiency (`QUERY_GROUPS`)
- [x] Budget cap per search session (`--budget` flag)

### Scoring (COMPLETE)

- [x] 4-factor weighted scoring: skills (40%) + title match (25%) + resume overlap (20%) + certs (15%)
- [x] Comprehensive skill alias matching (40+ canonical skills, 100+ aliases)
- [x] Certification matching (GSEC, GCIH, GCIA, Security+, CISSP, etc.)
- [x] Title matching against 9 target roles from profile
- [x] Resume keyword overlap analysis
- [x] Score tiers: STRONG (75%+), GOOD (60%+), MODERATE (45%+), WEAK (<45%)
- [x] `score` CLI command fully wired and tested
- [x] Profile auto-loaded from `job_search_profile.json` + `resume.txt`

### Application Prep (COMPLETE)

- [x] `prepare` CLI command fully wired
- [x] Tailored resume bullets using JD skills + user experience
- [x] Cover letter with real experience (PurpleLens, 60+ customers, certs)
- [x] Pre-filled screening answers (7 common questions)
- [x] Human review checklist with `[HUMAN:]` edit markers
- [x] Confirmation code generated for submit approval
- [x] Data security: resume/contact never transmitted

### Submission & Tracking (COMPLETE)

- [x] `submit` CLI command wired with confirmation code verification
- [x] `track` CLI command for opportunity status updates
- [x] Persistent `opportunities_log.json` with full history
- [x] All actions audit-logged to `job_search_audit.log`
- [ ] Actual form submission to job boards (currently generates apply URL — user submits manually)

### Automation & Alerts (COMPLETE)

- [x] Daily cron job installed: `0 16 * * 1-5` (9 AM Pacific, Mon-Fri)
- [x] Cron script at `/docker/openclaw-utxu/data/.openclaw/extensions/job-search-custom/daily_digest_cron.sh`
- [x] `digest` CLI command: searches all sites, scores, produces summary
- [x] Telegram-formatted digest output with emoji scoring indicators
- [x] Budget-capped daily runs (50 credits/day default)
- [x] Per-date digest archival in `digests/` directory
- [x] Auto pip install on each cron run (survives container restarts)
- [ ] Telegram push notification (currently digest outputs to stdout/log; agent must be asked to read it)
- [ ] Alert thresholds (notify on 80%+ match scores)

### Profile & Preferences (COMPLETE)

- [x] `job_search_profile.json` with 9 target roles
- [x] Target locations: Seattle/WA/Remote
- [x] Work arrangement: onsite, hybrid, remote
- [x] 23 key skills + 13 certifications listed
- [x] `resume.txt` with full resume text
- [x] Profile auto-loaded by all commands (score, prepare, digest)

### Utility Commands (COMPLETE)

- [x] `quota` — Show credit usage/remaining
- [x] `sites` — List all 8 job sites with status, JS requirement, cost

---

## Architecture

```
Telegram User (@clawgaurd_agent_bot)
    │
    ▼
OpenClaw Agent (Nexos GPT-5-2 model)
    │
    ├── Reads TOOLS.md (job search commands + profile)
    ├── Reads SKILL.md (skill capabilities)
    │
    ▼
job_search_secure.py (Python CLI)
    │
    ├── search  ──► Oxylabs AI Studio ──► LinkedIn (1cr) ✅
    │            │                     ──► Indeed (4cr)   ✅
    │            │                     ──► Monster (4cr)  ✅
    │            │                     ──► Dice (4cr)     ✅
    │            │                     ──► CyberSecJobs (1cr) ✅
    │            │                     ──► InfoSec Jobs (1cr) ✅
    │            │                     ──► SimplyHired (4cr)  ✅
    │            │                     ──► USAJobs (4cr)      ✅
    │            └── Deduplication + budget tracking
    │
    ├── score   ──► 4-factor weighted scoring vs resume + profile ✅
    ├── prepare ──► Tailored cover letter + resume bullets ✅
    ├── submit  ──► Human approval gate (confirmation code) ✅
    ├── digest  ──► Full daily report across all sites ✅
    ├── track   ──► opportunities_log.json ✅
    ├── quota   ──► Credit usage reporting ✅
    └── sites   ──► Site status listing ✅

Cron (VPS host): 9 AM Pacific Mon-Fri → daily_digest_cron.sh → digest command
```

## File Locations

### Local (Windows)
```
C:\Projects\ClawGuard\
├── PHASE1_PROGRESS.md              ← this file
├── OPENCLAW_PROJECT_SPEC.md        ← full project spec
├── CLAUDE_CODE_RUNBOOK_OPENCLAW.md ← deployment runbook
├── target-agent/
│   ├── skills/job-search-custom/
│   │   ├── SKILL.md                ← skill manifest (updated for 8 sites)
│   │   ├── AUDIT.md                ← security audit
│   │   ├── job_search_secure.py    ← main implementation (650+ lines)
│   │   ├── job_search_profile.json ← target roles/locations/skills
│   │   ├── resume.txt              ← plain text resume
│   │   └── daily_digest_cron.sh    ← VPS cron script
│   └── docs/
│       └── skill-test-log.md       ← test results
```

### VPS (31.97.139.139)
```
/docker/openclaw-utxu/
├── .env                                    ← API keys (Oxylabs, Telegram, Nexos)
├── docker-compose.yml                      ← container config
└── data/.openclaw/
    ├── openclaw.json                       ← main config
    ├── workspace/
    │   ├── TOOLS.md                        ← agent instructions (all commands + profile)
    │   ├── job_search_audit.log            ← audit trail
    │   └── opportunities_log.json          ← opportunity tracker
    ├── extensions/job-search-custom/
    │   ├── daily_digest_cron.sh            ← cron script (host-side)
    │   └── logs/                           ← cron output logs
    └── [container internal]
        /usr/local/lib/node_modules/openclaw/skills/job-search-custom/
        ├── job_search_secure.py            ← deployed skill
        ├── SKILL.md                        ← skill manifest
        ├── job_search_profile.json         ← profile
        ├── resume.txt                      ← resume
        ├── oxylabs_quota.json              ← persistent quota tracking
        └── digests/                        ← daily digest archives
```

## Key Lessons Learned

1. **Docker restart vs recreate:** `docker restart` does NOT re-read `.env`. Only `docker compose down && up` reloads env vars.
2. **Skills vs Extensions:** OpenClaw `extensions/` is for plugins. Agent skills live in `/usr/local/lib/node_modules/openclaw/skills/`. Custom skills must be copied there AND referenced in `TOOLS.md`.
3. **Indeed needs JS rendering:** Indeed blocks Oxylabs without `render_javascript=True` (4 credits). LinkedIn works without (1 credit).
4. **Credit budget math:** ~1 credit per no-JS page, ~4 per JS page. Budget of 50/day with 3 query groups × 8 sites is manageable.
5. **pip packages lost on recreate:** Container image is read-only. `pip install` must be re-run after `docker compose down && up`.
6. **Skill files in container lost on recreate:** Must re-copy via `docker cp` after recreation.
7. **Shell escaping for remote SSH:** Use base64 encoding to write files with backticks over SSH heredocs.
8. **Persistent quota:** Write quota tracking to JSON file inside container (survives restarts but not recreates).

## Oxylabs Credit Budget

| Action | Credits | Remaining |
|--------|---------|-----------|
| Initial quota | 0 | 1000 |
| Various tests (2026-03-24) | ~180 | ~820 |
| Multi-site test: LinkedIn+Dice+CyberSecJobs (2026-03-25) | ~7 | ~813 |
| **Current balance** | **~187 used** | **~813 remaining** |

**Budget strategy:** Daily digest at 50 credits/day = ~16 business days remaining. OR queries reduce 9 roles to 3 searches. Cheapest sites first (LinkedIn, CyberSecJobs, InfoSec Jobs at 1 credit each).

---

## Phase 1 Polish (Shipped 2026-03-25)

- [x] **JD enrichment** — Follows job detail URLs to scrape full descriptions (requirements, qualifications, responsibilities). Costs 1-4 extra credits per new job.
- [x] **Date filtering** — First week: shows all jobs (catch-up). After day 7: only last 24 hours.
- [x] **Apply URL cleanup** — LinkedIn URLs cleaned to direct `/jobs/view/` links, tracking params stripped.
- [x] **Email notifications** — Gmail SMTP with App Password, sent on compile step.
- [x] **PR #1 merged** — All Phase 1 work merged to main.

## Remaining Nice-to-Haves

- [ ] **Telegram push** — Currently digest prints to stdout (cron log). Could trigger OpenClaw agent to forward.
- [ ] **Alert thresholds** — Auto-notify on STRONG_MATCH (80%+) via separate Telegram message.
- [ ] **Direct form submission** — Currently generates apply URL for manual submission.
- [ ] **Profile preferences enforcement** — Filter by experience level, job type, salary range.

## Phase 2 & 3 (Future)

- **Phase 2:** Security monitoring agent (log analysis, alert triage)
- **Phase 3:** Learning/training agent (cert prep, lab automation)

---

*This document is designed for AI handoff. Any Claude/GPT/agent should be able to read this + the code and continue implementation.*
