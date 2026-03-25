---
name: job-search-custom
description: "Persistent job search pipeline with SQLite dedup, 9-site staggered search, resume scoring, auto-prepared application materials, and Telegram+email notifications. Human approval required."
metadata:
  openclaw:
    requires:
      env:
        - OXYLABS_AISTUDIO_API_KEY
      bins:
        - python3
    primaryEnv: OXYLABS_AISTUDIO_API_KEY
---

# Job Search Custom Skill v2

**Persistent, multi-site job search pipeline with one-stop-shop application prep.**

Searches 9 job boards on a staggered schedule, deduplicates across runs via SQLite, scores against resume/profile, auto-prepares tailored materials for strong matches, and notifies via Telegram + email. All data stays local. Human approval required.

## Architecture

```
9:00 AM  → LinkedIn    (1 cr)  → DB insert (dedup) → score
9:30 AM  → CyberSecJobs (1 cr) → DB insert (dedup) → score
10:00 AM → InfoSecJobs  (1 cr) → DB insert (dedup) → score
10:30 AM → Indeed       (4 cr) → DB insert (dedup) → score
11:00 AM → Dice         (4 cr) → DB insert (dedup) → score
11:30 AM → Monster      (4 cr) → DB insert (dedup) → score
12:00 PM → SimplyHired  (4 cr) → DB insert (dedup) → score
12:00 PM → RemoteHunter (4 cr) → DB insert (dedup) → score
12:30 PM → USAJobs      (4 cr) → DB insert (dedup) → score
 1:00 PM → COMPILE: score all → auto-prepare 60%+ → Telegram + Email
```

## Commands

### Initialize Database (run once)
```bash
python3 job_search_secure.py init-db
```

### Search Jobs
```bash
# Single site (default: LinkedIn)
python3 job_search_secure.py search --query "SOC Analyst" --location "Seattle, WA"

# All 9 sites with budget cap
python3 job_search_secure.py search --query "Security Engineer" --location "Seattle, WA" --sites all --budget 30

# Specific sites
python3 job_search_secure.py search --query "Threat Hunter" --location "Remote" --sites linkedin,dice,cybersecjobs
```

### Score Jobs
```bash
# Score all "found" jobs in DB against resume
python3 job_search_secure.py score --status found --min-score 0.40

# Score from legacy JSON file
python3 job_search_secure.py score --jobs results.json
```

### Prepare Application Materials
```bash
python3 job_search_secure.py prepare --job-id "abc123def456"
```
Creates `/data/clawguard/applications/{job_id}/` with:
- `metadata.json` — apply URL, score, status
- `jd.txt` — full job description
- `resume_tailored.md` — rule-governed tailored resume
- `cover_letter.md` — cover letter draft
- `screening_answers.json` — pre-filled Q&A
- `review_checklist.md` — human review items

### Daily Digest
```bash
# Single-site staggered run (called by cron)
python3 job_search_secure.py digest --site linkedin --budget 6

# Compile today's results (no new searches)
python3 job_search_secure.py digest --compile --format telegram

# Full run (all sites + compile)
python3 job_search_secure.py digest --budget 50 --format telegram
```

### Browse Database
```bash
# Pipeline summary
python3 job_search_secure.py browse --summary

# Today's new jobs
python3 job_search_secure.py browse

# Jobs by status
python3 job_search_secure.py browse --status scored

# Single job details
python3 job_search_secure.py browse --job-id abc123

# Jobs from last 24 hours
python3 job_search_secure.py browse --since 24h
```

### Track & Submit
```bash
# Update job status
python3 job_search_secure.py track --job-id abc123 --status applied

# Approve submission (requires confirmation code from prepare)
python3 job_search_secure.py submit --job-id abc123 --confirmation-code A1B2C3D4
```

### Utility
```bash
python3 job_search_secure.py quota    # Credit usage
python3 job_search_secure.py sites    # List all 9 sites
python3 job_search_secure.py export --status scored --output scored.json
python3 job_search_secure.py migrate --source /path/to/old/digests/
```

## Supported Sites

| Site | Key | JS | Credits | Niche |
|------|-----|----|---------|-------|
| LinkedIn | linkedin | No | 1 | General |
| Indeed | indeed | Yes | 4 | Volume |
| Monster | monster | Yes | 4 | Traditional |
| Dice | dice | Yes | 4 | Tech/IT |
| CyberSecJobs | cybersecjobs | No | 1 | Cybersecurity |
| InfoSec Jobs | infosecjobs | No | 1 | InfoSec |
| SimplyHired | simplyhired | Yes | 4 | Aggregator |
| USAJobs | usajobs | Yes | 4 | Government |
| RemoteHunter | remotehunter | Yes | 4 | Remote work |

## Data Storage

All persistent data at `/data/clawguard/` (Docker volume, survives restarts):
```
/data/clawguard/
  jobs.db                    — SQLite database (all jobs, scores, status)
  tailoring_rules.json       — Resume tailoring rules
  applications/{job_id}/     — Per-job materials
  digests/                   — Daily digest archives
  logs/                      — Cron and search logs
```

## Resume Tailoring Rules

Materials are generated using `tailoring_rules.json`:
- **No fabrication** — only skills/experience from resume.txt
- **No embellishment** — actual metrics only (50% MTTR, 60+ clients, etc.)
- **Pre-approved bullet templates** traced to specific resume sections
- **[HUMAN:]** markers for anything requiring your judgment

## Security

- Resume and contact info NEVER sent to job boards
- All API calls logged to audit trail
- Confirmation code required for submission approval
- No auto-submit capability exists
- Email credentials stored in .env only, never in code

## When to Use

Use when user asks to:
- Search for jobs or find openings
- Score/rank jobs against resume
- Prepare cover letters or application materials
- Run daily digest or check new matches
- Browse the job database or check pipeline status
- Track application status
- Check credit quota

**Always use this skill instead of web_search for job-related queries.**
