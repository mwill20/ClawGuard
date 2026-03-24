---
name: job-search-custom
description: Secure job search and preparation for OpenClaw. Search multiple job boards (Indeed, LinkedIn, Glassdoor, ZipRecruiter) using Oxylabs AI Studio, score matches against your resume, and prepare tailored application materials. Human review required before any submission. No auto-submit. No data exfiltration.
metadata:
  openclaw:
    requires:
      env:
        - OXYLABS_AISTUDIO_API_KEY
      bins:
        - python3
        - curl
    primaryEnv: OXYLABS_AISTUDIO_API_KEY
---

# Job Search Custom Skill

**Secure, audited job search and preparation tool for OpenClaw agents.**

Searches job boards, scores matches against your resume, generates tailored cover letters, and prepares application materials. **All data stays local.** **Human approval required before any action.** **No auto-submit, no credential theft, no hidden API calls.**

## Overview

This skill is the guardrails-first alternative to community job-auto-apply skills. It provides:

1. **Search** — Query Indeed, LinkedIn, Glassdoor, ZipRecruiter via Oxylabs API (primary) or FireCrawl (fallback)
2. **Score** — Compare job descriptions to your resume using TF-IDF + skill extraction
3. **Prepare** — Generate tailored resume bullets and cover letter drafts
4. **Track** — Log opportunities in structured JSON (your control)
5. **Review** — Human approval before any submission (no automatic actions)

## When to Use This Skill

- You want to automate job searching across multiple boards
- You need resume tailoring and cover letter generation
- You prefer human-in-the-loop control (all actions require approval)
- You want transparent, audited code with no hidden exfiltration vectors
- You have Oxylabs API credits and want to use them securely

## Quick Start

### 1. Set Up Your Resume and Profile

Create a profile JSON with your resume and preferences:

```json
{
  "full_name": "Your Name",
  "email": "[your-email]@example.com",
  "phone": "+1-555-0000",
  "resume_text": "Full resume text or parsed content here...",
  "target_roles": ["SOC Analyst II", "Security Engineer", "Threat Hunter"],
  "target_locations": ["Remote", "Seattle, WA"],
  "preferences": {
    "min_salary": 100000,
    "job_type": ["full-time"],
    "remote_only": false
  }
}
```

### 2. Search Jobs

```bash
python job_search_secure.py search \
  --profile ~/my_profile.json \
  --query "SOC Analyst" \
  --locations "Remote,Seattle" \
  --max_results 10
```

Output: A list of jobs with metadata (title, company, description, URL, match_score).

### 3. Review and Score

```bash
python job_search_secure.py score \
  --job_file ~/found_jobs.json \
  --profile ~/my_profile.json \
  --min_score 0.70
```

Output: Ranked list of jobs by match score, with a "PREPARE" recommendation for top 3.

### 4. Prepare Application

```bash
python job_search_secure.py prepare \
  --job_id "indeed_12345" \
  --profile ~/my_profile.json \
  --output ~/drafts/job_12345_prep.json
```

Output: A JSON file containing:
- **resume_bullets**: Tailored resume bullets for this role
- **cover_letter_draft**: Full cover letter draft
- **answers_to_common_questions**: Pre-filled answers to standard screening questions
- **action_required**: Human review checklist before submission

### 5. Submit (Manual Only)

Review the prepared materials in `job_12345_prep.json`. If approved:

```bash
python job_search_secure.py submit_manual \
  --prepared_file ~/drafts/job_12345_prep.json \
  --confirmation_code "<human-enters-this>"
```

**Note:** No automatic submission. The agent prepares, you review, you decide.

## Core Functions

### `search(query, locations, max_results=10)`

**Inputs:**
- `query`: Job title or keywords (e.g., "SOC Analyst", "Security Engineer")
- `locations`: List of locations (e.g., ["Remote", "Seattle, WA"])
- `max_results`: Max jobs to return (default 10, max 50 per API limits)

**Primary method:** Oxylabs AI Studio API
- Parses Indeed, LinkedIn, Glassdoor, ZipRecruiter using intelligent data extraction
- Returns structured job data: title, company, description, salary (if available), posting URL

**Fallback method:** FireCrawl (if Oxylabs rate limit hit or disabled)
- Browser-based crawl of job board pages
- Slower but reliable fallback

**Output:**
```json
{
  "job_id": "indeed_12345",
  "title": "SOC Analyst II",
  "company": "Acme Corp",
  "location": "Seattle, WA",
  "job_type": "full-time",
  "salary_range": "$120k - $150k",
  "description": "...full job description text...",
  "url": "https://indeed.com/...",
  "source": "indeed",
  "posted_date": "2026-03-20"
}
```

### `score(jobs, resume_text, min_threshold=0.60)`

**Inputs:**
- `jobs`: List of job objects from `search()`
- `resume_text`: Your resume as text
- `min_threshold`: Minimum match score (0-1)

**Scoring logic:**
1. Extract required skills from job description (NLP)
2. Extract your skills from resume
3. Calculate TF-IDF overlap + exact skill matches
4. Return score (0 = no match, 1 = perfect match)

**Output:**
```json
{
  "job_id": "indeed_12345",
  "score": 0.82,
  "matched_skills": ["Python", "AWS", "Incident Response"],
  "missing_skills": ["Kubernetes"],
  "recommendation": "STRONG_MATCH",
  "reasoning": "85% of required skills present, salary within range"
}
```

### `prepare(job, resume, profile)`

**Inputs:**
- `job`: Job object from `search()`
- `resume`: Your full resume
- `profile`: Your professional profile (name, email, phone, etc.)

**Generates:**
1. **Resume bullets** — 3-5 tailored resume points for this role
2. **Cover letter** — Full cover letter draft addressing role-specific needs
3. **Common answers** — Pre-filled answers to typical screening questions:
   - "Why do you want to work here?"
   - "What interests you about this role?"
   - "Describe a challenge you overcame..."
4. **Checklist** — Human review points before submission

**Output:**
```json
{
  "job_id": "indeed_12345",
  "resume_bullets": [
    "Detected and remediated 50+ security incidents using SIEM automation",
    "Developed Python-based alert triage reducing false positives by 40%",
    "..."
  ],
  "cover_letter_draft": "Dear Hiring Manager...",
  "common_answers": {
    "why_this_company": "Your company's focus on...",
    "why_this_role": "I'm drawn to the SOC Analyst II role because...",
    "challenge_example": "In my previous role, I..."
  },
  "human_review_checklist": [
    "[ ] Review resume bullets for accuracy",
    "[ ] Edit cover letter tone and personalization",
    "[ ] Verify salary expectations are correct",
    "[ ] Confirm you meet all required qualifications"
  ]
}
```

### `track_opportunity(job, prepared_materials, status, notes="")`

**Inputs:**
- `job`: Job object
- `prepared_materials`: Output from `prepare()`
- `status`: "prepared", "submitted", "interviewed", "rejected", "offer"
- `notes`: Optional notes (interviewer feedback, etc.)

**Output:** Appends to `opportunities_log.json` with full history.

## Security & Audit Notes

### Data Flow

✅ **All data stays local:**
- Your resume is never sent to job boards
- Your contact info is never sent to job boards
- Personal details are only used in locally-generated documents

✅ **No hidden API calls:**
- Only Oxylabs (Oxylabs API) and FireCrawl (OpenClaw built-in) are called
- All API calls are logged and visible

✅ **No auto-submit:**
- Every submission requires human review + confirmation code
- Agent cannot submit without your explicit approval

### Environment Variables

```bash
# Required
export OXYLABS_AISTUDIO_API_KEY="your_api_key_here"

# Optional (for fallback)
# FireCrawl is built into OpenClaw, no config needed
```

### Logging

All operations logged to `job_search_audit.log`:
```
2026-03-24 14:32:15 [SEARCH] Query="SOC Analyst" Locations="Remote,Seattle" Results=8
2026-03-24 14:33:02 [SCORE] Job="indeed_12345" Score=0.82 Status="STRONG_MATCH"
2026-03-24 14:34:18 [PREPARE] Job="indeed_12345" Generated_materials=true
2026-03-24 14:35:45 [SUBMIT_MANUAL] Job="indeed_12345" Confirmation_received=true Status="submitted"
```

## Rate Limits & Costs

**Oxylabs:**
- Your subscription includes 1,000 credits (from Hostinger)
- ~10 credits per job search query
- Cost-effective for 50-100 job searches

**FireCrawl (fallback):**
- Built into OpenClaw, no additional cost
- Use when Oxylabs quota exhausted

## Example Workflow

```bash
# 1. Search for jobs
python job_search_secure.py search \
  --query "SOC Analyst II" \
  --locations "Remote" \
  --max_results 20

# 2. Score matches (filters to top 5 with 0.75+ score)
python job_search_secure.py score \
  --job_file ~/searches/soc_analyst_20.json \
  --profile ~/my_profile.json \
  --min_score 0.75

# 3. Prepare application for top match
python job_search_secure.py prepare \
  --job_id "indeed_54321" \
  --profile ~/my_profile.json \
  --output ~/drafts/indeed_54321.json

# 4. Human reviews ~/drafts/indeed_54321.json
# (edits cover letter, tweaks bullets, etc.)

# 5. Submit with confirmation
python job_search_secure.py submit_manual \
  --prepared_file ~/drafts/indeed_54321.json \
  --confirmation_code "READY_TO_SUBMIT_12345"

# 6. Track in log
python job_search_secure.py track \
  --job_id "indeed_54321" \
  --status "submitted" \
  --notes "Applied via OpenClaw on 2026-03-24"
```

## Troubleshooting

**Q: Oxylabs API rate limit hit?**
A: `search()` automatically falls back to FireCrawl. Check the log to see which method was used.

**Q: Cover letter draft feels generic?**
A: Edit it! The agent prepares a starting point. You refine it before submission. No auto-submit means quality control is in your hands.

**Q: How do I track my applications?**
A: Use `track()` command. Your `opportunities_log.json` contains the full history with status, date, and notes.

## Comparison to Original `job-auto-apply`

| Feature | Original | Secure Version |
|---|---|---|
| Auto-submit? | Yes (risky) | No (human approval only) |
| Data exfiltration risk? | High (unknown API calls) | None (logged, transparent) |
| Resume security? | Unclear | Stays local, never sent to boards |
| Audit trail? | Minimal | Full event log + prep materials |
| Code review? | Not guaranteed | This file documents every function |
| Rate limiting? | Basic | Strict + fallback strategy |
| Customization? | Limited | Full control at each step |

---

**Author:** Built for ClawGuard project. Designed with guardrails-first philosophy. Every function is transparent, every action is auditable, no exceptions.
