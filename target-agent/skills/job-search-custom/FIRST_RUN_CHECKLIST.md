# First Live Run Observation Checklist — 2026-03-26

**Expected compile time:** 1:00 PM Pacific (20:00 UTC)
**Check at:** 1:05 PM Pacific

---

## Quick Health Check

```bash
ssh root@31.97.139.139

# 1. Did cron fire? Check logs for each site
tail -20 /docker/openclaw-utxu/data/clawguard/logs/cron.log

# 2. How many jobs found today?
KEY=$(grep "^OXYLABS_AISTUDIO_API_KEY=" /docker/openclaw-utxu/.env | cut -d= -f2)
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" -e CLAWGUARD_DATA_DIR="/data/clawguard" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 python3 job_search_secure.py browse --summary

# 3. Today's digest
cat /docker/openclaw-utxu/data/clawguard/digests/digest_2026-03-26.json | python3 -m json.tool | head -30

# 4. Per-site job counts (baseline data)
cat /docker/openclaw-utxu/data/clawguard/logs/search_*_2026-03-26.log | grep "Found.*jobs"

# 5. Credit usage
docker exec -e OXYLABS_AISTUDIO_API_KEY="$KEY" -e CLAWGUARD_DATA_DIR="/data/clawguard" \
  -w /usr/local/lib/node_modules/openclaw/skills/job-search-custom \
  openclaw-utxu-openclaw-1 python3 job_search_secure.py quota

# 6. Application packages created
ls -la /docker/openclaw-utxu/data/clawguard/applications/

# 7. Any errors?
grep -i "error\|failed\|exception" /docker/openclaw-utxu/data/clawguard/logs/cron.log | tail -10
```

---

## Observation Matrix

| Signal | Expected | Concern If | Action |
|--------|----------|------------|--------|
| Total jobs in digest | 15-40 | 0 = cron didn't fire, 100+ = queries too broad | Check cron.log |
| Jobs scored 60%+ | 3-10 | 0 = scoring too strict | Lower MIN_SCORE_THRESHOLD |
| Auto-prepared packages | 2-8 | 0 = no 60%+ matches | Check scoring weights |
| JD enrichment rate | 80%+ of new jobs | <50% = detail scrape failing | Check site-specific errors |
| Credits used | 30-60 | >80 = budget cap not working | Check budget_limit logic |
| Email received | Yes | No = Gmail SMTP issue | Check compile log |
| Per-site breakdown | Even across sites | 0 from any site = that site blocked | Disable failing sites |

---

## Spot-Check Protocol (Pick 2-3 Jobs)

For each spot-checked job:

1. **Score feels right?**
   - Open `applications/{job_id}/metadata.json` — check score + recommendation
   - Open `applications/{job_id}/jd.txt` — read the actual JD
   - Does the score match your gut feel? (e.g., a SOC Analyst role with SIEM/EDR requirements should be 70%+)

2. **Application package coherent?**
   - `resume_tailored.md` — are the bullets accurate? Any fabrication?
   - `cover_letter.md` — does it reference real experience (PurpleLens, 60+ clients)?
   - `screening_answers.json` — are the [HUMAN:] markers in the right places?

3. **URL works?**
   - Click the apply_url in metadata.json — does it go to the actual job posting?
   - If it goes to a company page, note the source site (LinkedIn URL issue)

---

## Baseline Data to Capture

After the run, record these numbers (they become your drift detection baseline):

```
Date: 2026-03-26
LinkedIn:      ___ jobs found, ___ new, ___ enriched
CyberSecJobs:  ___ jobs found, ___ new, ___ enriched
InfoSec Jobs:  ___ jobs found, ___ new, ___ enriched
Indeed:        ___ jobs found, ___ new, ___ enriched
Dice:          ___ jobs found, ___ new, ___ enriched
Monster:       ___ jobs found, ___ new, ___ enriched
SimplyHired:   ___ jobs found, ___ new, ___ enriched
RemoteHunter:  ___ jobs found, ___ new, ___ enriched
USAJobs:       ___ jobs found, ___ new, ___ enriched
─────────────
Total:         ___ jobs, ___ new, ___ enriched
Credits used:  ___
Strong matches: ___
Good matches:   ___
Auto-prepared:  ___
Anomalies:      ___
```

---

## Anomaly Log

| Time | Observation | Severity | Action Taken |
|------|-------------|----------|--------------|
| | | | |
