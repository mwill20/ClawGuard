# OpenClaw Phase 1 Progress — Job Hunting Agent

**Last Updated:** 2026-03-24
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

# Test search directly in container
docker exec openclaw-utxu-openclaw-1 python3 \
  /data/.openclaw/extensions/job-search-custom/job_search_secure.py \
  search --query "SOC Analyst" --location "Seattle, WA" --max-results 5

# View audit log
cat /docker/openclaw-utxu/data/.openclaw/workspace/job_search_audit.log

# Restart after changes (just restart, NOT recreate)
docker restart openclaw-utxu-openclaw-1

# If you change .env, you MUST recreate (restart does NOT re-read .env):
cd /docker/openclaw-utxu && docker compose down && docker compose up -d

# Re-install pip package after container recreate:
docker exec openclaw-utxu-openclaw-1 pip install oxylabs-ai-studio --break-system-packages
```

---

## Phase 1 Scope: Job Hunting Agent (Use Case 1 of 3)

### Overall Progress: ~60%

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

- [x] `SKILL.md` in `/data/.openclaw/extensions/job-search-custom/`
- [x] `AUDIT.md` in `/data/.openclaw/extensions/job-search-custom/`
- [x] `job_search_secure.py` in `/data/.openclaw/extensions/job-search-custom/`
- [x] `SKILL.md` copied to built-in skills dir (`/usr/local/lib/node_modules/openclaw/skills/job-search-custom/`) — **NOTE: lost on container recreate, must re-copy**
- [x] `TOOLS.md` updated with job search instructions and profile
- [x] Agent correctly routes "search for jobs" to `job-search-custom` skill

### Search (PARTIALLY COMPLETE)

- [x] Oxylabs AI Studio SDK integration (real API calls, not stubs)
- [x] LinkedIn scraping — working, returns real job listings
- [ ] Indeed scraping — blocked without JS rendering, needs `render_javascript=True` or alt approach
- [ ] Glassdoor scraping — not implemented
- [ ] ZipRecruiter scraping — not implemented
- [ ] Wellfound scraping — not implemented
- [ ] Monster scraping — not implemented
- [ ] Dice scraping — not implemented
- [ ] Google Jobs scraping — not implemented
- [x] Rate limiting (5s between searches, 50 result cap)
- [x] Quota tracking (started 1000 credits, ~870 remaining as of 2026-03-24)
- [ ] Multi-keyword search (run all 9 target roles in one session)
- [ ] Combined OR query to conserve credits

### Scoring (STUBBED)

- [x] `score_job()` function exists with TF-IDF structure
- [x] `extract_skills()` has 28 hardcoded security skills
- [ ] Wire `score` CLI command to `main()` (parser exists, dispatch missing)
- [ ] Integrate `resume.txt` into scoring (currently not loaded from file)
- [ ] Integrate `job_search_profile.json` skills/certs into matching
- [ ] Dynamic skill extraction from job descriptions (currently hardcoded list)
- [ ] Weighted scoring (required vs. nice-to-have skills)

### Application Prep (STUBBED)

- [x] `prepare_application()` function exists with template structure
- [x] Cover letter template with `[HUMAN: ...]` edit markers
- [x] Human review checklist generated
- [x] Data security flags (resume never transmitted)
- [ ] Wire `prepare` CLI command to `main()` (parser exists, dispatch missing)
- [ ] Real resume bullet tailoring (currently 3 generic bullets)
- [ ] Role-specific talking points in cover letter
- [ ] Load profile from `job_search_profile.json`

### Submission & Tracking (PARTIALLY COMPLETE)

- [x] `submit_manual()` with SHA256 confirmation code gate
- [x] `track_opportunity()` writes to `opportunities_log.json`
- [x] `track` CLI command implemented
- [ ] Wire `submit` CLI command to `main()`
- [ ] Actual form submission to job boards (currently logs only)
- [ ] Opportunity status tracking in daily digest

### Automation & Alerts (NOT STARTED)

- [ ] Daily cron job for automated search across all target roles
- [ ] Telegram daily digest (top matches, new listings)
- [ ] Configurable search schedule (cron via OpenClaw `/data/.openclaw/cron/jobs.json`)
- [ ] Alert thresholds (notify on 80%+ match scores)

### Profile & Preferences (COMPLETE)

- [x] `job_search_profile.json` with 9 target roles
- [x] Target locations: Seattle/WA/Remote
- [x] Work arrangement: onsite, hybrid, remote
- [x] 32 key skills + 8 certifications listed
- [x] `resume.txt` uploaded to VPS workspace
- [ ] Profile preferences enforced in search filtering (experience level, job type)

---

## Architecture

```
Telegram User (@clawgaurd_agent_bot)
    │
    ▼
OpenClaw Agent (Nexos GPT-5-2 model)
    │
    ├── Reads TOOLS.md (knows about job-search-custom)
    ├── Reads SKILL.md (knows skill capabilities)
    │
    ▼
job_search_secure.py (Python CLI)
    │
    ├── search  ──► Oxylabs AI Studio ──► LinkedIn (working)
    │                                  ──► Indeed (blocked, needs JS)
    │                                  ──► [7 more sites TODO]
    ├── score   ──► TF-IDF vs resume (stubbed)
    ├── prepare ──► Cover letter + bullets (stubbed)
    ├── submit  ──► Human approval gate (stubbed)
    └── track   ──► opportunities_log.json (working)
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
│   │   ├── SKILL.md                ← skill manifest
│   │   ├── AUDIT.md                ← security audit
│   │   ├── job_search_secure.py    ← main implementation
│   │   ├── job_search_profile.json ← target roles/locations
│   │   └── resume.txt              ← plain text resume
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
    │   ├── TOOLS.md                        ← agent instructions (has job search profile)
    │   ├── resume.txt                      ← resume for scoring
    │   ├── job_search_audit.log            ← audit trail
    │   └── opportunities_log.json          ← opportunity tracker
    ├── extensions/job-search-custom/
    │   ├── SKILL.md, AUDIT.md              ← skill docs
    │   ├── job_search_secure.py            ← implementation
    │   ├── job_search_profile.json         ← preferences
    │   └── resume.txt                      ← resume copy
    └── cron/jobs.json                      ← scheduled tasks (empty)
```

## Key Lessons Learned

1. **Docker restart vs recreate:** `docker restart` does NOT re-read `.env`. Only `docker compose down && up` reloads env vars.
2. **Skills vs Extensions:** OpenClaw `extensions/` is for plugins. Agent skills live in `/usr/local/lib/node_modules/openclaw/skills/`. Custom skills must be copied there AND referenced in `TOOLS.md`.
3. **Indeed blocks Oxylabs:** Indeed returns empty data without JS rendering. LinkedIn works without JS rendering (1 credit vs 4 credits per page).
4. **Oxylabs credit budget:** ~10 credits per result. 1000 total credits = ~100 results. Need combined queries to conserve credits.
5. **pip packages lost on recreate:** Container image is read-only. `pip install` must be re-run after `docker compose down && up`.
6. **SKILL.md in skills dir lost on recreate:** Must re-copy after container recreation.

## Oxylabs Credit Budget

| Action | Credits Used | Remaining |
|--------|-------------|-----------|
| Initial (quota) | 0 | 1000 |
| Test: SOC Analyst Remote (CLI) | ~50 | ~950 |
| Test: SOC Analyst Seattle (CLI) | ~30 | ~920 |
| Test: Security Engineer Seattle (Telegram) | ~100 | ~820 |
| **Current balance** | **~180 used** | **~820 remaining** |

**Budget strategy:** At ~10 credits/result, ~820 credits = ~82 more job results. Use combined OR queries and limit to 2-3 sites to stay within budget.

---

## Next Steps (Priority Order)

1. **Wire remaining CLI commands** — `score`, `prepare`, `submit` dispatchers in `main()`
2. **Multi-site search** — Add Indeed (with JS rendering), Glassdoor, Google Jobs URL templates
3. **Real scoring** — Load `resume.txt`, use profile skills/certs for matching
4. **Daily digest cron** — Configure OpenClaw cron to run morning search + Telegram summary
5. **Credit-efficient searching** — Combined OR queries across target roles

---

*This document is designed for AI handoff. Any Claude/GPT/agent should be able to read this + the code and continue Phase 1 implementation.*
