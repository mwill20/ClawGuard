---
name: job-search-custom
description: "Secure multi-site job search with resume scoring and application prep. Searches LinkedIn, Indeed, Monster, Dice, CyberSecJobs, InfoSec Jobs, SimplyHired, USAJobs. Scores matches against resume/profile. Prepares tailored cover letters and materials. Daily digest mode for scheduled runs. Human approval required before any submission."
metadata:
  openclaw:
    requires:
      env:
        - OXYLABS_AISTUDIO_API_KEY
      bins:
        - python3
    primaryEnv: OXYLABS_AISTUDIO_API_KEY
---

# Job Search Custom Skill

**Secure, multi-site job search with resume scoring and application prep for OpenClaw agents.**

Searches 8 job boards, scores matches against your resume and profile, generates tailored materials, and runs daily digests. **All data stays local.** **Human approval required.** **No auto-submit.**

## Commands

### 1. Search Jobs

```bash
# Single site (default: LinkedIn, cheapest at 1 credit)
python3 job_search_secure.py search \
  --query "SOC Analyst" \
  --location "Seattle, WA" \
  --max-results 10

# Multi-site search
python3 job_search_secure.py search \
  --query "Security Engineer OR Detection Engineer" \
  --location "Seattle, WA" \
  --sites all \
  --budget 30

# Specific sites
python3 job_search_secure.py search \
  --query "Threat Hunter" \
  --location "Remote" \
  --sites linkedin,dice,cybersecjobs \
  --output results.json
```

### 2. Score Jobs Against Resume

```bash
python3 job_search_secure.py score \
  --jobs results.json \
  --min-score 0.40 \
  --output scored.json
```

Scoring factors (weighted):
- **40%** Skill match (EDR, SIEM, Python, etc.)
- **25%** Title match (target roles from profile)
- **20%** Resume keyword overlap
- **15%** Certification match (GSEC, GCIH, etc.)

### 3. Prepare Application Materials

```bash
python3 job_search_secure.py prepare \
  --job-id "abc123def456" \
  --job-file results.json \
  --output materials.json
```

Generates: tailored resume bullets, cover letter draft, screening answers, review checklist.

### 4. Submit (Human Approval Only)

```bash
python3 job_search_secure.py submit \
  --prepared materials.json \
  --confirmation-code "A1B2C3D4"
```

### 5. Daily Digest (Scheduled Mode)

```bash
# Full daily digest across all sites with budget cap
python3 job_search_secure.py digest \
  --budget 50 \
  --min-score 0.40 \
  --format telegram

# JSON format for programmatic use
python3 job_search_secure.py digest --format json
```

### 6. Utility Commands

```bash
# Check credit quota
python3 job_search_secure.py quota

# List available sites
python3 job_search_secure.py sites

# Track opportunity status
python3 job_search_secure.py track --job-id "abc123" --status "applied"
```

## Supported Job Sites

| Site | Key | JS Render | Credits | Best For |
|------|-----|-----------|---------|----------|
| LinkedIn | `linkedin` | No | 1 | General, most listings |
| Indeed | `indeed` | Yes | 4 | Volume, salary data |
| Monster | `monster` | Yes | 4 | Traditional job board |
| Dice | `dice` | Yes | 4 | Tech/IT specific |
| CyberSecJobs | `cybersecjobs` | No | 1 | Cybersecurity niche |
| InfoSec Jobs | `infosecjobs` | No | 1 | InfoSec niche |
| SimplyHired | `simplyhired` | Yes | 4 | Aggregator |
| USAJobs | `usajobs` | Yes | 4 | Government/cleared |

## Credit Budget

- 1,000 credits/month (Oxylabs via Hostinger)
- Daily digest at 50 credits/day = ~20 business days coverage
- Use `quota` command to check remaining credits

## Security

- Resume and contact info NEVER sent to job boards
- All API calls logged to `job_search_audit.log`
- Confirmation code required for any submission
- No auto-submit capability exists in the code

## When to Use This Skill

Use when the user asks to:
- Search for jobs, find job openings, look for positions
- Score or rank jobs against their resume
- Prepare cover letters or application materials
- Run a daily job search digest
- Check job search credit quota
- Track application status

**Always use this skill instead of web_search for job-related queries.**
