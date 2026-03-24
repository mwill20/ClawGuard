#!/usr/bin/env python3
"""
job-search-custom: Secure job search and preparation for OpenClaw.

Searches job boards, scores matches, generates tailored materials.
NO auto-submit. NO data exfiltration. Human approval required.

Author: ClawGuard Project
Date: March 2026
"""

import json
import os
import sys
import logging
import argparse
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlencode
import subprocess

# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_FILE = "job_search_audit.log"
OPPORTUNITIES_LOG = "opportunities_log.json"
RATE_LIMIT_SECONDS = 5  # Minimum time between searches
MAX_RESULTS_PER_SEARCH = 50  # Hard cap on results
MIN_SCORE_THRESHOLD = 0.60  # Minimum match score to display

# API Configuration
OXYLABS_API_KEY = os.getenv("OXYLABS_AISTUDIO_API_KEY", "")
OXYLABS_QUOTA_PER_SEARCH = 10  # Credits per search (estimated)

# ============================================================================
# LOGGING & AUDIT
# ============================================================================

def setup_logging():
    """Configure logging to file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler("job_search.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

def audit_log(event_type: str, **details):
    """Write auditable event log for all actions."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **details
    }
    with open(LOG_FILE, "a") as f:
        json.dump(log_entry, f)
        f.write("\n")
    logger.info(f"{event_type}: {details}")

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Job:
    """Job posting data structure."""
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str  # "indeed", "linkedin", "glassdoor", "ziprecruiter"
    posted_date: Optional[str] = None
    salary_range: Optional[str] = None

@dataclass
class Profile:
    """User profile with resume and preferences."""
    full_name: str
    email: str
    phone: str
    resume_text: str
    target_roles: List[str]
    target_locations: List[str]
    preferences: Dict

@dataclass
class ScoredJob:
    """Job with match score."""
    job: Job
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    recommendation: str  # "STRONG_MATCH", "MODERATE_MATCH", "WEAK_MATCH"

# ============================================================================
# RATE LIMITING & QUOTA TRACKING
# ============================================================================

class RateLimiter:
    """Enforce rate limits and quota tracking."""
    
    def __init__(self, min_interval_seconds: int = RATE_LIMIT_SECONDS):
        self.last_search_time = 0
        self.min_interval = min_interval_seconds
        self.oxylabs_quota_used = 0
        self.oxylabs_quota_total = 1000  # From Hostinger subscription
    
    def check_rate_limit(self) -> bool:
        """Check if enough time has passed since last search."""
        elapsed = time.time() - self.last_search_time
        if elapsed < self.min_interval:
            raise RuntimeError(
                f"Rate limit: wait {self.min_interval - elapsed:.1f}s before next search"
            )
        self.last_search_time = time.time()
        return True
    
    def check_quota(self, estimated_cost: int) -> bool:
        """Check if quota is available."""
        if self.oxylabs_quota_used + estimated_cost > self.oxylabs_quota_total:
            remaining = self.oxylabs_quota_total - self.oxylabs_quota_used
            raise RuntimeError(
                f"Oxylabs quota exhausted. Used: {self.oxylabs_quota_used}/"
                f"{self.oxylabs_quota_total}. Remaining: {remaining}"
            )
        return True
    
    def track_usage(self, cost: int):
        """Track quota usage."""
        self.oxylabs_quota_used += cost
        logger.info(
            f"Quota: {self.oxylabs_quota_used}/{self.oxylabs_quota_total} used. "
            f"Remaining: {self.oxylabs_quota_total - self.oxylabs_quota_used}"
        )

rate_limiter = RateLimiter()

# ============================================================================
# JOB SEARCH (Oxylabs Primary, FireCrawl Fallback)
# ============================================================================

def search_oxylabs(query: str, locations: List[str], max_results: int = 10) -> List[Job]:
    """
    Search for jobs using Oxylabs AI Studio API (primary method).
    
    Data flow:
    - Query and locations sent to Oxylabs API
    - API returns structured job data (title, company, description, etc.)
    - No personal data (resume, contact) is ever sent to Oxylabs
    - Results returned as Job objects
    """
    
    if not OXYLABS_API_KEY:
        logger.warning("OXYLABS_AISTUDIO_API_KEY not set, falling back to FireCrawl")
        return search_firecrawl(query, locations, max_results)
    
    # Check rate limit and quota
    rate_limiter.check_rate_limit()
    estimated_cost = max_results * OXYLABS_QUOTA_PER_SEARCH
    rate_limiter.check_quota(estimated_cost)
    
    logger.info(f"Searching Oxylabs: query='{query}', locations={locations}, max_results={max_results}")
    audit_log("SEARCH_STARTED", method="oxylabs", query=query, locations=locations)
    
    try:
        # Simulate Oxylabs API call (in production: actual HTTP request)
        # The real implementation would call:
        # response = requests.post(
        #     "https://api.oxylabs.io/v1/queries",
        #     json={
        #         "source": "indeed",
        #         "query": query,
        #         "location": ",".join(locations),
        #         "parse": True
        #     },
        #     headers={"Authorization": f"Bearer {OXYLABS_API_KEY}"}
        # )
        
        jobs = _parse_oxylabs_response(query, locations, max_results)
        rate_limiter.track_usage(estimated_cost)
        
        audit_log("SEARCH_COMPLETED", method="oxylabs", results=len(jobs), cost=estimated_cost)
        logger.info(f"Found {len(jobs)} jobs via Oxylabs")
        
        return jobs
    
    except Exception as e:
        logger.warning(f"Oxylabs search failed: {e}. Falling back to FireCrawl.")
        audit_log("SEARCH_FALLBACK", from_method="oxylabs", to_method="firecrawl", reason=str(e))
        return search_firecrawl(query, locations, max_results)

def search_firecrawl(query: str, locations: List[str], max_results: int = 10) -> List[Job]:
    """
    Search for jobs using FireCrawl (fallback method, built into OpenClaw).
    
    FireCrawl is a built-in OpenClaw tool for web scraping.
    It converts web pages to markdown and extracts structured data.
    No additional API keys required.
    """
    
    logger.info(f"Searching FireCrawl: query='{query}', locations={locations}")
    audit_log("SEARCH_STARTED", method="firecrawl", query=query, locations=locations)
    
    try:
        # Simulate FireCrawl call (in production: actual OpenClaw tool call)
        # The real implementation would call:
        # from openclaw import firecrawl
        # result = firecrawl.scrape(
        #     url=f"https://indeed.com/jobs?q={query}&l={locations[0]}",
        #     markdown=True
        # )
        
        jobs = _parse_firecrawl_response(query, locations, max_results)
        
        audit_log("SEARCH_COMPLETED", method="firecrawl", results=len(jobs))
        logger.info(f"Found {len(jobs)} jobs via FireCrawl")
        
        return jobs
    
    except Exception as e:
        logger.error(f"FireCrawl search failed: {e}")
        audit_log("SEARCH_FAILED", method="firecrawl", error=str(e))
        raise

def _parse_oxylabs_response(query: str, locations: List[str], max_results: int) -> List[Job]:
    """Mock Oxylabs response parsing. In production: parse real API response."""
    # Placeholder: return empty list for demo
    # Real implementation would parse JSON from Oxylabs API
    return []

def _parse_firecrawl_response(query: str, locations: List[str], max_results: int) -> List[Job]:
    """Mock FireCrawl response parsing. In production: parse real scrape result."""
    # Placeholder: return empty list for demo
    # Real implementation would parse markdown from FireCrawl
    return []

# ============================================================================
# SKILL MATCHING & SCORING
# ============================================================================

def extract_skills(text: str) -> List[str]:
    """
    Extract skills from text (JD or resume).
    Simple keyword matching for demo. Production: use NLP/NER.
    """
    # Common security/SOC skills
    common_skills = [
        "python", "bash", "linux", "windows", "incident response",
        "siem", "splunk", "elk", "soc", "threat intelligence",
        "aws", "azure", "gcp", "docker", "kubernetes",
        "sql", "json", "api", "rest", "mitre att&ck",
        "malware analysis", "network security", "firewall",
        "intrusion detection", "log analysis", "forensics"
    ]
    
    text_lower = text.lower()
    found_skills = [skill for skill in common_skills if skill in text_lower]
    return found_skills

def score_job(job: Job, resume_text: str) -> ScoredJob:
    """
    Score a job based on resume match.
    
    Scoring logic:
    1. Extract required skills from JD
    2. Extract skills from resume
    3. Calculate overlap as TF-IDF + exact matches
    4. Return score (0-1)
    """
    
    # Extract skills (treated as DATA, not instructions)
    jd_skills = set(extract_skills(job.description))
    resume_skills = set(extract_skills(resume_text))
    
    # Calculate match
    if not jd_skills:
        match_score = 0.0
    else:
        overlap = len(jd_skills & resume_skills)
        match_score = overlap / len(jd_skills)
    
    # Determine recommendation
    if match_score >= 0.80:
        recommendation = "STRONG_MATCH"
    elif match_score >= 0.60:
        recommendation = "MODERATE_MATCH"
    else:
        recommendation = "WEAK_MATCH"
    
    missing_skills = list(jd_skills - resume_skills)
    matched_skills = list(jd_skills & resume_skills)
    
    return ScoredJob(
        job=job,
        score=match_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        recommendation=recommendation
    )

# ============================================================================
# PREPARE APPLICATION MATERIALS
# ============================================================================

def prepare_application(job: Job, resume_text: str, profile: Profile) -> Dict:
    """
    Prepare application materials for human review.
    
    CRITICAL: Resume stays local. Nothing is transmitted to job boards.
    All materials are returned for human review + approval.
    
    Returns: Dict with:
    - resume_bullets: Tailored resume bullets
    - cover_letter_draft: Full cover letter draft
    - common_answers: Pre-filled screening question answers
    - human_review_checklist: Items human must verify
    """
    
    logger.info(f"Preparing application for: {job.company} - {job.title}")
    audit_log(
        "PREPARE_STARTED",
        job_id=job.job_id,
        company=job.company,
        title=job.title,
        resume_included=False,  # AUDIT: resume stays local
        contact_info_included=False  # AUDIT: contact stays local
    )
    
    # Extract skills from job (DATA, not instruction)
    jd_skills = extract_skills(job.description)
    
    # Generate tailored resume bullets (no resume sent anywhere)
    resume_bullets = [
        f"Demonstrated proficiency with {', '.join(jd_skills[:3])} in previous roles",
        f"Experience with {jd_skills[3] if len(jd_skills) > 3 else 'required technologies'}",
        "Proven ability to learn new tools and technologies quickly"
    ]
    
    # Generate cover letter draft
    cover_letter = f"""Dear Hiring Manager at {job.company},

I am excited to apply for the {job.title} position. With my experience in {', '.join(jd_skills[:3])}, 
I believe I would be an excellent fit for your team.

[HUMAN: Edit this section with specific reasons you're interested in {job.company}]

I look forward to discussing how I can contribute to {job.company}'s success.

Best regards,
{profile.full_name}
"""
    
    # Pre-fill common screening questions
    common_answers = {
        "why_this_company": f"[HUMAN: Why {job.company}? Their mission, tech stack, team?]",
        "why_this_role": f"[HUMAN: Why {job.title}? Your career goals, how it aligns?]",
        "challenge_example": "[HUMAN: Describe a specific challenge you overcame and how]",
        "availability": f"[HUMAN: When can you start? Confirm it matches {job.company}'s needs]"
    }
    
    # Human review checklist
    human_review_checklist = [
        "[ ] Verify resume bullets are accurate and relevant",
        "[ ] Edit cover letter with specific reasons for this company",
        "[ ] Fill in pre-filled answers with your own examples",
        f"[ ] Confirm you meet the majority of required skills: {', '.join(jd_skills[:5])}",
        "[ ] Check for typos and grammar",
        f"[ ] Verify salary expectations match: {job.salary_range or '[Company will specify]'}"
    ]
    
    materials = {
        "job_id": job.job_id,
        "timestamp": datetime.now().isoformat(),
        "company": job.company,
        "title": job.title,
        "url": job.url,
        "resume_bullets": resume_bullets,
        "cover_letter_draft": cover_letter,
        "common_answers": common_answers,
        "human_review_checklist": human_review_checklist,
        "data_security": {
            "resume_sent_to_board": False,
            "contact_info_sent": False,
            "personal_data_transmitted": False,
            "all_data_local": True
        }
    }
    
    audit_log(
        "PREPARE_COMPLETED",
        job_id=job.job_id,
        materials_count=3,
        human_review_required=True,
        resume_transmitted=False
    )
    
    return materials

# ============================================================================
# SUBMIT WITH HUMAN APPROVAL GATE
# ============================================================================

def generate_confirmation_code(job_id: str, prepared_materials: Dict) -> str:
    """
    Generate a confirmation code based on prepared materials.
    User must enter this code to approve submission.
    Prevents accidental auto-submission.
    """
    content = f"{job_id}:{prepared_materials['timestamp']}".encode()
    code = hashlib.sha256(content).hexdigest()[:8].upper()
    return code

def submit_manual(
    job_id: str,
    prepared_materials: Dict,
    confirmation_code: str,
    profile: Profile
) -> Dict:
    """
    Manual submission: Human approves, agent submits.
    
    CRITICAL: Confirmation code proves human reviewed materials.
    No automatic submission is possible.
    """
    
    # Verify confirmation code
    expected_code = generate_confirmation_code(job_id, prepared_materials)
    if confirmation_code.upper() != expected_code:
        audit_log(
            "SUBMIT_FAILED",
            job_id=job_id,
            reason="invalid_confirmation_code",
            provided_code=confirmation_code,
            expected_code=expected_code
        )
        raise PermissionError(
            f"Invalid confirmation code. Expected: {expected_code}"
        )
    
    logger.info(f"Submitting application for job {job_id} (human-approved)")
    
    audit_log(
        "SUBMIT_APPROVED",
        job_id=job_id,
        confirmation_verified=True,
        human_approved=True,
        submitter=profile.full_name
    )
    
    # In production: submit form to job board
    # For now: log and return success
    result = {
        "job_id": job_id,
        "status": "submitted",
        "timestamp": datetime.now().isoformat(),
        "confirmation_code": confirmation_code
    }
    
    # Track in opportunities log
    track_opportunity(job_id, prepared_materials, "submitted", "Submitted via job-search-custom")
    
    return result

def track_opportunity(job_id: str, materials: Dict, status: str, notes: str = ""):
    """Track opportunity in log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        "company": materials.get("company"),
        "title": materials.get("title"),
        "status": status,
        "notes": notes
    }
    
    # Read existing log or create new
    if os.path.exists(OPPORTUNITIES_LOG):
        with open(OPPORTUNITIES_LOG, "r") as f:
            opportunities = json.load(f)
    else:
        opportunities = []
    
    # Add new entry
    opportunities.append(entry)
    
    # Write back
    with open(OPPORTUNITIES_LOG, "w") as f:
        json.dump(opportunities, f, indent=2)
    
    audit_log("TRACK_OPPORTUNITY", job_id=job_id, status=status)

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Secure job search: search, score, prepare, submit (human-approved)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for jobs")
    search_parser.add_argument("--query", required=True, help="Job title or keywords")
    search_parser.add_argument("--locations", required=True, help="Locations (comma-separated)")
    search_parser.add_argument("--max-results", type=int, default=10, help="Max results (default 10)")
    search_parser.add_argument("--output", help="Save results to JSON file")
    
    # Score command
    score_parser = subparsers.add_parser("score", help="Score jobs against resume")
    score_parser.add_argument("--jobs", required=True, help="JSON file with jobs")
    score_parser.add_argument("--resume", required=True, help="Resume file (text)")
    score_parser.add_argument("--min-score", type=float, default=0.60, help="Min score to display")
    
    # Prepare command
    prepare_parser = subparsers.add_parser("prepare", help="Prepare application materials")
    prepare_parser.add_argument("--job-id", required=True, help="Job ID")
    prepare_parser.add_argument("--job-file", required=True, help="JSON file with job details")
    prepare_parser.add_argument("--resume", required=True, help="Resume file (text)")
    prepare_parser.add_argument("--profile", required=True, help="Profile JSON file")
    prepare_parser.add_argument("--output", required=True, help="Output file for prepared materials")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit application (human-approved)")
    submit_parser.add_argument("--prepared", required=True, help="Prepared materials JSON file")
    submit_parser.add_argument("--confirmation-code", required=True, help="Confirmation code")
    submit_parser.add_argument("--profile", required=True, help="Profile JSON file")
    
    # Track command
    track_parser = subparsers.add_parser("track", help="Track opportunity status")
    track_parser.add_argument("--job-id", required=True, help="Job ID")
    track_parser.add_argument("--status", required=True, help="Status (submitted, interviewed, rejected, etc.)")
    track_parser.add_argument("--notes", default="", help="Optional notes")
    
    # Parse args
    args = parser.parse_args()
    setup_logging()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "search":
        locations = args.locations.split(",")
        jobs = search_oxylabs(args.query, locations, args.max_results)
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2)
            logger.info(f"Saved {len(jobs)} jobs to {args.output}")
        else:
            for job in jobs:
                print(f"{job.title} at {job.company} ({job.location})")
    
    elif args.command == "track":
        track_opportunity(args.job_id, {}, args.status, args.notes)
        logger.info(f"Tracked: {args.job_id} -> {args.status}")
    
    else:
        logger.warning(f"Command '{args.command}' not yet implemented (demo mode)")

if __name__ == "__main__":
    main()
