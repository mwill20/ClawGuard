# V2 Extensions — Future Enhancements

Documented features for future implementation. These are NOT in v1 but should be built when the core pipeline is stable.

## 1. Fellowship & Grant Opportunities Search

**Goal:** Daily web search for cybersecurity and AI security fellowship/grant opportunities.

**Approach:**
- Use OpenClaw's web_search (Brave API) or Oxylabs to search:
  - "cybersecurity fellowship 2026"
  - "AI security fellowship application"
  - "CISA cybersecurity fellowship"
  - "SANS fellowship"
  - "CyberCorps Scholarship for Service"
  - "NSF cybersecurity grant"
- Store in a separate `fellowships` table in jobs.db
- Different scoring: weight on educational background, AI/ML certs, research experience
- Once per day, low credit cost (web search, not site scraping)

**Schedule:** Add one cron entry at 8:30 AM Pacific (before job search starts)

## 2. LinkedIn Post Monitoring for Hiring Signals

**Goal:** Search LinkedIn posts (not job listings) for hiring managers posting about open roles.

**Approach:**
- Search LinkedIn for posts containing:
  - "we're hiring" + (SOC Analyst | Security Engineer | Threat Hunter)
  - "join my team" + cybersecurity
  - "open role" + security
  - "#hiring" + security engineer
- Oxylabs can scrape LinkedIn post search results
- Extract: poster name, company, role mentioned, post URL
- Store in `linkedin_posts` table
- Alert on posts from target companies or matching target roles

**Credit cost:** ~4 credits/search (JS rendering needed for LinkedIn posts)

**Schedule:** Once daily at 8:00 AM Pacific

## 3. Company Research Enrichment

**Goal:** When auto-preparing materials, scrape the company's website for context.

**Approach:**
- For each STRONG/GOOD match, scrape company's about page
- Extract: mission statement, tech stack mentions, recent news
- Auto-fill the `[HUMAN: Why this company?]` placeholder with research notes
- Store in `company_research` table for reuse across jobs at same company

## 4. Salary Intelligence

**Goal:** Track salary data across all scraped jobs to build market intelligence.

**Approach:**
- Parse salary_range field into min/max numbers
- Aggregate by role title, location, company size
- Generate weekly salary report: "Security Engineer in Seattle: $130K-$180K (n=45)"
- Use for negotiation prep and expectations setting

## 5. Application Success Tracking

**Goal:** Track apply → response → interview → offer pipeline metrics.

**Approach:**
- Add `response_date`, `interview_dates[]`, `offer_details` columns
- Weekly pipeline report: conversion rates, average response time
- Pattern detection: which sites/companies respond fastest

## 6. Smart Scheduling Based on Site Freshness

**Goal:** Don't waste credits on sites that rarely have new jobs.

**Approach:**
- Track new_jobs/search ratio per site over 30 days
- Reduce frequency for low-yield sites (e.g., USAJobs → 2x/week)
- Increase frequency for high-yield sites (e.g., LinkedIn → 2x/day)
- Dynamic budget allocation based on ROI

## 7. Resume Version Management

**Goal:** Track which version of tailored resume was sent to which company.

**Approach:**
- Git-like versioning of resume_tailored.md per application
- Diff view between general resume and tailored version
- Prevent accidentally sending outdated resume to new applications

## 8. Interview Prep Integration

**Goal:** When status changes to "interview", auto-generate prep materials.

**Approach:**
- Pull company Glassdoor reviews (interview questions)
- Generate STAR-format answers based on resume experience
- Create "cheat sheet" with company facts, interviewer LinkedIn profiles
- Save to applications/{job_id}/interview_prep.md

---

*These extensions should be prioritized based on pipeline stability and credit budget. Fellowship search (1) and LinkedIn monitoring (2) are highest priority as they expand opportunity coverage with minimal credit cost.*
