#!/usr/bin/env python3
"""
job-search-custom: Secure job search and preparation for OpenClaw.

Searches job boards, scores matches, generates tailored materials.
NO auto-submit. NO data exfiltration. Human approval required.

Supported sites: LinkedIn, Indeed, Monster, Dice, CyberSecJobs,
                 InfoSec Jobs, SimplyHired, USAJobs
Author: ClawGuard Project
Date: March 2026
"""

import json
import os
import sys
import logging
import argparse
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from urllib.parse import quote_plus, urlencode
import subprocess

# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_FILE = "job_search_audit.log"
OPPORTUNITIES_LOG = "opportunities_log.json"
DIGEST_OUTPUT = "daily_digest.json"
RATE_LIMIT_SECONDS = 5  # Minimum time between searches
MAX_RESULTS_PER_SEARCH = 50  # Hard cap on results
MIN_SCORE_THRESHOLD = 0.40  # Minimum match score to display

# API Configuration
OXYLABS_API_KEY = os.getenv("OXYLABS_AISTUDIO_API_KEY", "")
OXYLABS_QUOTA_PER_PAGE = 1       # Credits per page (no JS rendering)
OXYLABS_QUOTA_PER_PAGE_JS = 4    # Credits per page (with JS rendering)

# Skill base directory (where this script lives)
SKILL_DIR = Path(__file__).parent.resolve()

# ============================================================================
# SITE CONFIGURATIONS
# ============================================================================
# Each site: url_builder, needs_js, credits_per_page, notes

SITE_CONFIGS = {
    "linkedin": {
        "name": "LinkedIn",
        "url_builder": lambda q, loc: (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={quote_plus(q)}&location={quote_plus(loc)}"
        ),
        "needs_js": False,
        "credits_per_page": 1,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "indeed": {
        "name": "Indeed",
        "url_builder": lambda q, loc: (
            f"https://www.indeed.com/jobs"
            f"?q={quote_plus(q)}&l={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "monster": {
        "name": "Monster",
        "url_builder": lambda q, loc: (
            f"https://www.monster.com/jobs/search"
            f"?q={quote_plus(q)}&where={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "dice": {
        "name": "Dice",
        "url_builder": lambda q, loc: (
            f"https://www.dice.com/jobs"
            f"?q={quote_plus(q)}&location={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "cybersecjobs": {
        "name": "CyberSecJobs",
        "url_builder": lambda q, loc: (
            f"https://www.cybersecurityjobs.com/jobs/"
            f"?q={quote_plus(q)}&location={quote_plus(loc)}"
        ),
        "needs_js": False,
        "credits_per_page": 1,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "infosecjobs": {
        "name": "InfoSec Jobs",
        "url_builder": lambda q, loc: (
            f"https://infosec-jobs.com/jobs/"
            f"?search={quote_plus(q)}&location={quote_plus(loc)}"
        ),
        "needs_js": False,
        "credits_per_page": 1,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "simplyhired": {
        "name": "SimplyHired",
        "url_builder": lambda q, loc: (
            f"https://www.simplyhired.com/search"
            f"?q={quote_plus(q)}&l={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
        "schema_hint": "job_listings",
    },
    "usajobs": {
        "name": "USAJobs",
        "url_builder": lambda q, loc: (
            f"https://www.usajobs.gov/Search/Results"
            f"?k={quote_plus(q)}&l={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
        "schema_hint": "job_listings",
    },
}

# Credit-efficient combined query groups
# Instead of searching 9 roles individually, group into OR queries
QUERY_GROUPS = [
    "SOC Analyst OR SOC Engineer OR Security Operations Engineer",
    "Security Engineer OR Detection Engineer OR AI Security Engineer",
    "Threat Hunter OR Customer Success Engineer cybersecurity",
]

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
    source: str  # "linkedin", "indeed", "monster", "dice", etc.
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
    key_skills: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

@dataclass
class ScoredJob:
    """Job with match score."""
    job: Job
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    matched_certs: List[str]
    title_match: bool
    recommendation: str  # "STRONG_MATCH", "GOOD_MATCH", "MODERATE_MATCH", "WEAK_MATCH"

# ============================================================================
# RATE LIMITING & QUOTA TRACKING
# ============================================================================

QUOTA_FILE = "oxylabs_quota.json"

class RateLimiter:
    """Enforce rate limits and quota tracking with persistent storage."""

    def __init__(self, min_interval_seconds: int = RATE_LIMIT_SECONDS):
        self.last_search_time = 0
        self.min_interval = min_interval_seconds
        self.oxylabs_quota_total = 1000  # From Hostinger subscription
        self._load_quota()

    def _load_quota(self):
        """Load persistent quota tracking."""
        if os.path.exists(QUOTA_FILE):
            try:
                with open(QUOTA_FILE, "r") as f:
                    data = json.load(f)
                self.oxylabs_quota_used = data.get("used", 0)
                self.oxylabs_quota_total = data.get("total", 1000)
                self._month = data.get("month", datetime.now().strftime("%Y-%m"))
                # Reset if new month
                if self._month != datetime.now().strftime("%Y-%m"):
                    logger.info("New month — resetting quota counter")
                    self.oxylabs_quota_used = 0
                    self._month = datetime.now().strftime("%Y-%m")
            except (json.JSONDecodeError, KeyError):
                self.oxylabs_quota_used = 0
                self._month = datetime.now().strftime("%Y-%m")
        else:
            self.oxylabs_quota_used = 180  # ~180 already used this month
            self._month = datetime.now().strftime("%Y-%m")

    def _save_quota(self):
        """Persist quota to disk."""
        with open(QUOTA_FILE, "w") as f:
            json.dump({
                "used": self.oxylabs_quota_used,
                "total": self.oxylabs_quota_total,
                "month": self._month,
                "last_updated": datetime.now().isoformat(),
            }, f, indent=2)

    def check_rate_limit(self) -> bool:
        """Check if enough time has passed since last search."""
        elapsed = time.time() - self.last_search_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.info(f"Rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        self.last_search_time = time.time()
        return True

    def check_quota(self, estimated_cost: int) -> bool:
        """Check if quota is available."""
        if self.oxylabs_quota_used + estimated_cost > self.oxylabs_quota_total:
            remaining = self.oxylabs_quota_total - self.oxylabs_quota_used
            raise RuntimeError(
                f"Oxylabs quota low. Used: {self.oxylabs_quota_used}/"
                f"{self.oxylabs_quota_total}. Remaining: {remaining}. "
                f"Estimated cost: {estimated_cost}"
            )
        return True

    def track_usage(self, cost: int):
        """Track quota usage and persist."""
        self.oxylabs_quota_used += cost
        self._save_quota()
        remaining = self.oxylabs_quota_total - self.oxylabs_quota_used
        logger.info(
            f"Quota: {self.oxylabs_quota_used}/{self.oxylabs_quota_total} used. "
            f"Remaining: {remaining}"
        )

    def get_remaining(self) -> int:
        return self.oxylabs_quota_total - self.oxylabs_quota_used

rate_limiter = RateLimiter()

# ============================================================================
# JOB SEARCH ENGINE
# ============================================================================

# Shared Oxylabs schema for all job sites
JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "job_listings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_title":    {"type": "string"},
                    "company_name": {"type": "string"},
                    "location":     {"type": "string"},
                    "apply_url":    {"type": "string"},
                    "salary":       {"type": "string"},
                    "date_posted":  {"type": "string"},
                    "description":  {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}


def search_site(
    site_key: str,
    query: str,
    location: str,
    max_results: int = 10,
) -> List[Job]:
    """
    Search a specific job site using Oxylabs AI Studio.

    Args:
        site_key: Key from SITE_CONFIGS (e.g. "linkedin", "indeed")
        query: Search query (job title, keywords, OR combinations)
        location: Single location string
        max_results: Max results to return

    Returns:
        List of Job objects
    """
    config = SITE_CONFIGS.get(site_key)
    if not config:
        logger.error(f"Unknown site: {site_key}")
        return []
    if not config.get("enabled", True):
        logger.info(f"Site {site_key} is disabled, skipping")
        return []

    if not OXYLABS_API_KEY:
        logger.error("OXYLABS_AISTUDIO_API_KEY not set")
        return []

    credits = config["credits_per_page"]
    rate_limiter.check_rate_limit()
    rate_limiter.check_quota(credits)

    url = config["url_builder"](query, location)
    needs_js = config["needs_js"]

    logger.info(f"Searching {config['name']}: query='{query}', location='{location}', js={needs_js}")
    audit_log("SEARCH_STARTED", method="oxylabs", site=site_key, query=query, location=location)

    try:
        from oxylabs_ai_studio.apps.ai_scraper import AiScraper

        scraper = AiScraper(api_key=OXYLABS_API_KEY)
        result = scraper.scrape(
            url=url,
            output_format="json",
            schema=JOB_SCHEMA,
            render_javascript=needs_js,
            geo_location="US",
        )

        data = result.data if result else {}
        jobs = _parse_oxylabs_response(data, site_key, location, max_results)
        rate_limiter.track_usage(credits)

        audit_log("SEARCH_COMPLETED", site=site_key, results=len(jobs), cost=credits)
        logger.info(f"Found {len(jobs)} jobs on {config['name']}")
        return jobs

    except Exception as e:
        logger.warning(f"{config['name']} search failed: {e}")
        audit_log("SEARCH_FAILED", site=site_key, error=str(e))
        return []


def search_oxylabs(query: str, locations: List[str], max_results: int = 10) -> List[Job]:
    """
    Legacy single-site search (LinkedIn). Kept for backward compatibility.
    For multi-site, use search_all_sites() or search_site() directly.
    """
    location_str = locations[0] if locations else "Remote"
    return search_site("linkedin", query, location_str, max_results)


def search_firecrawl(query: str, locations: List[str], max_results: int = 10) -> List[Job]:
    """FireCrawl fallback — placeholder for future OpenClaw native integration."""
    logger.info("FireCrawl fallback not yet implemented")
    return []


def search_all_sites(
    query: str,
    location: str,
    sites: Optional[List[str]] = None,
    max_results_per_site: int = 10,
    budget_limit: Optional[int] = None,
) -> List[Job]:
    """
    Search across multiple job sites with deduplication.

    Args:
        query: Search query
        location: Location string
        sites: List of site keys (default: all enabled sites)
        max_results_per_site: Max results per site
        budget_limit: Max credits to spend (None = no limit)

    Returns:
        Deduplicated list of Job objects from all sites
    """
    if sites is None:
        sites = [k for k, v in SITE_CONFIGS.items() if v.get("enabled", True)]

    all_jobs = []
    credits_spent = 0
    sites_searched = 0
    sites_failed = []

    for site_key in sites:
        config = SITE_CONFIGS.get(site_key, {})
        site_cost = config.get("credits_per_page", 4)

        # Budget check
        if budget_limit and credits_spent + site_cost > budget_limit:
            logger.info(f"Budget limit reached ({credits_spent}/{budget_limit}), stopping")
            break

        try:
            jobs = search_site(site_key, query, location, max_results_per_site)
            all_jobs.extend(jobs)
            credits_spent += site_cost
            sites_searched += 1
        except RuntimeError as e:
            logger.warning(f"Skipping {site_key}: {e}")
            sites_failed.append(site_key)
        except Exception as e:
            logger.warning(f"Error searching {site_key}: {e}")
            sites_failed.append(site_key)

    # Deduplicate by title+company (fuzzy)
    deduped = _deduplicate_jobs(all_jobs)

    logger.info(
        f"Multi-site search complete: {len(deduped)} unique jobs from "
        f"{sites_searched} sites ({credits_spent} credits). "
        f"Failed: {sites_failed or 'none'}"
    )
    return deduped


def _deduplicate_jobs(jobs: List[Job]) -> List[Job]:
    """Remove duplicate jobs based on normalized title+company."""
    seen = set()
    unique = []
    for job in jobs:
        key = _normalize_for_dedup(job.title, job.company)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _normalize_for_dedup(title: str, company: str) -> str:
    """Normalize title+company for dedup comparison."""
    t = re.sub(r'[^a-z0-9]', '', title.lower())
    c = re.sub(r'[^a-z0-9]', '', company.lower())
    return f"{t}|{c}"


def _parse_oxylabs_response(
    data: dict,
    site_key: str,
    location: str,
    max_results: int,
) -> List[Job]:
    """Parse Oxylabs AI Studio JSON response into Job objects."""
    if not data:
        return []

    # Find job list — try known key first, then fall back to first list value
    job_list = data.get("job_listings") or []
    if not job_list:
        for value in data.values():
            if isinstance(value, list) and value:
                job_list = value
                break

    jobs = []
    for item in job_list[:max_results]:
        if not isinstance(item, dict):
            continue

        title   = item.get("job_title") or item.get("title") or item.get("position") or "Unknown Title"
        company = item.get("company_name") or item.get("company") or item.get("employer") or "Unknown Company"
        loc     = item.get("location") or item.get("job_location") or location
        desc    = item.get("description") or item.get("job_description") or item.get("summary") or ""
        url     = item.get("apply_url") or item.get("url") or item.get("link") or ""
        salary  = item.get("salary") or item.get("salary_range") or item.get("compensation")
        posted  = item.get("date_posted") or item.get("posted") or item.get("date")

        job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
        jobs.append(Job(
            job_id=job_id,
            title=str(title),
            company=str(company),
            location=str(loc),
            description=str(desc),
            url=str(url),
            source=site_key,
            posted_date=str(posted) if posted else None,
            salary_range=str(salary) if salary else None,
        ))

    return jobs


# ============================================================================
# PROFILE & RESUME LOADING
# ============================================================================

def load_profile(profile_path: Optional[str] = None) -> Profile:
    """Load profile from JSON file + resume text."""
    if profile_path is None:
        profile_path = str(SKILL_DIR / "job_search_profile.json")

    with open(profile_path, "r") as f:
        data = json.load(f)

    # Load resume text
    resume_path = data.get("resume_path") or str(SKILL_DIR / "resume.txt")
    resume_text = ""
    if os.path.exists(resume_path):
        with open(resume_path, "r") as f:
            resume_text = f.read()

    return Profile(
        full_name=data.get("full_name", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        resume_text=resume_text,
        target_roles=data.get("target_roles", []),
        target_locations=data.get("target_locations", []),
        preferences=data.get("preferences", {}),
        key_skills=data.get("key_skills", []),
        certifications=data.get("certifications", []),
    )


# ============================================================================
# SKILL MATCHING & SCORING
# ============================================================================

# Comprehensive skills dictionary with aliases/variants
SKILL_ALIASES = {
    # Security tools
    "edr": ["edr", "endpoint detection", "endpoint detection and response"],
    "siem": ["siem", "security information", "log management"],
    "soar": ["soar", "security orchestration", "automation and response"],
    "fortiedr": ["fortiedr", "forti edr"],
    "fortisiem": ["fortisiem", "forti siem"],
    "swimlane": ["swimlane"],
    "splunk": ["splunk"],
    "sentinel": ["sentinel", "microsoft sentinel", "azure sentinel"],
    "wazuh": ["wazuh"],
    "trend micro": ["trend micro", "trendmicro", "trend micro xdr"],
    "crowdstrike": ["crowdstrike", "falcon"],
    "palo alto": ["palo alto", "cortex", "xsoar", "prisma"],
    "qradar": ["qradar"],

    # Security domains
    "incident response": ["incident response", "ir ", "incident handling"],
    "threat hunting": ["threat hunting", "threat hunt", "proactive hunting"],
    "threat intelligence": ["threat intelligence", "threat intel", "cti"],
    "malware analysis": ["malware analysis", "malware reverse", "reverse engineering"],
    "vulnerability management": ["vulnerability management", "vuln management", "vulnerability assessment"],
    "penetration testing": ["penetration testing", "pentest", "pen test", "ethical hacking"],
    "forensics": ["forensics", "forensic", "dfir", "digital forensics"],
    "soc": ["soc ", "security operations center", "security operations"],
    "detection engineering": ["detection engineering", "detection rules", "sigma rules", "yara"],
    "devsecops": ["devsecops", "dev sec ops", "secure sdlc"],

    # Cloud & Infra
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker", "container"],
    "kubernetes": ["kubernetes", "k8s"],

    # Programming & Tools
    "python": ["python"],
    "bash": ["bash", "shell script"],
    "powershell": ["powershell"],
    "sql": ["sql", "sqlite", "postgresql", "mysql"],
    "rest api": ["rest api", "api", "apis", "rest"],
    "git": ["git", "github", "gitlab"],

    # Frameworks
    "mitre att&ck": ["mitre att&ck", "mitre attack", "att&ck", "mitre"],
    "nist": ["nist", "nist 800"],
    "iso 27001": ["iso 27001", "iso27001"],
    "cis": ["cis benchmark", "cis controls"],

    # Soft skills (relevant for customer-facing roles)
    "customer success": ["customer success", "customer facing", "client facing"],
    "documentation": ["documentation", "technical writing"],
    "communication": ["communication", "stakeholder", "reporting"],

    # AI/ML (emerging niche)
    "llm": ["llm", "large language model", "ai/ml", "machine learning"],
    "ai security": ["ai security", "ml security", "mlsecops", "ai risk"],
}

# Certification aliases
CERT_ALIASES = {
    "gsec": ["gsec", "giac security essentials"],
    "gcih": ["gcih", "giac certified incident handler"],
    "gcia": ["gcia", "giac certified intrusion analyst"],
    "security+": ["security+", "comptia security", "sec+"],
    "cysa+": ["cysa+", "comptia cysa", "cybersecurity analyst+"],
    "pentest+": ["pentest+", "comptia pentest"],
    "casp+": ["casp+", "comptia advanced security practitioner"],
    "securityx": ["securityx", "comptia securityx"],
    "sscp": ["sscp", "systems security certified"],
    "cissp": ["cissp", "certified information systems security"],
    "ccna": ["ccna", "cisco certified network associate"],
    "ceh": ["ceh", "certified ethical hacker"],
    "oscp": ["oscp", "offensive security certified"],
    "az-500": ["az-500", "azure security engineer"],
    "sc-200": ["sc-200", "security operations analyst"],
    "itil": ["itil"],
    "caiss": ["caiss"],
}


def extract_skills_advanced(text: str, skill_dict: Optional[Dict] = None) -> List[str]:
    """
    Extract skills from text using comprehensive alias matching.

    Returns list of canonical skill names found in text.
    """
    if skill_dict is None:
        skill_dict = SKILL_ALIASES

    text_lower = text.lower()
    found = []
    for canonical, aliases in skill_dict.items():
        for alias in aliases:
            if alias in text_lower:
                found.append(canonical)
                break
    return found


def extract_certs(text: str) -> List[str]:
    """Extract certifications from text."""
    return extract_skills_advanced(text, CERT_ALIASES)


def score_job(job: Job, profile: Profile) -> ScoredJob:
    """
    Score a job against the full profile (resume + skills + certs + roles).

    Scoring breakdown (0-1):
      - Skill match:  40% weight — overlap of profile skills with JD
      - Cert match:   15% weight — certifications mentioned in JD that user has
      - Title match:  25% weight — does job title match target roles?
      - Resume match: 20% weight — keyword overlap between resume and JD
    """
    jd_text = f"{job.title} {job.description}".lower()

    # 1. Skill match (40%)
    jd_skills = set(extract_skills_advanced(jd_text))
    profile_skills = set(extract_skills_advanced(" ".join(profile.key_skills)))
    resume_skills = set(extract_skills_advanced(profile.resume_text))
    all_user_skills = profile_skills | resume_skills

    if jd_skills:
        matched_skills = list(jd_skills & all_user_skills)
        missing_skills = list(jd_skills - all_user_skills)
        skill_score = len(matched_skills) / len(jd_skills)
    else:
        matched_skills = []
        missing_skills = []
        skill_score = 0.3  # Neutral if no skills detected in JD

    # 2. Cert match (15%)
    jd_certs = set(extract_certs(jd_text))
    user_certs = set(extract_certs(" ".join(profile.certifications)))
    matched_certs = list(jd_certs & user_certs)
    cert_score = len(matched_certs) / len(jd_certs) if jd_certs else 0.5

    # 3. Title match (25%)
    title_lower = job.title.lower()
    title_match = any(
        role.lower() in title_lower or title_lower in role.lower()
        for role in profile.target_roles
    )
    # Also check partial matches (e.g., "Security Engineer" matches "Senior Security Engineer")
    if not title_match:
        title_match = any(
            all(word in title_lower for word in role.lower().split())
            for role in profile.target_roles
        )
    title_score = 1.0 if title_match else 0.2

    # 4. Resume keyword match (20%) — broader text similarity
    resume_words = set(re.findall(r'\b\w{4,}\b', profile.resume_text.lower()))
    jd_words = set(re.findall(r'\b\w{4,}\b', jd_text))
    if jd_words:
        resume_overlap = len(resume_words & jd_words) / len(jd_words)
        resume_score = min(resume_overlap * 2, 1.0)  # Scale up, cap at 1
    else:
        resume_score = 0.3

    # Weighted total
    total = (
        skill_score * 0.40 +
        cert_score * 0.15 +
        title_score * 0.25 +
        resume_score * 0.20
    )

    # Recommendation tiers
    if total >= 0.75:
        recommendation = "STRONG_MATCH"
    elif total >= 0.60:
        recommendation = "GOOD_MATCH"
    elif total >= 0.45:
        recommendation = "MODERATE_MATCH"
    else:
        recommendation = "WEAK_MATCH"

    return ScoredJob(
        job=job,
        score=round(total, 3),
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_certs=matched_certs,
        title_match=title_match,
        recommendation=recommendation,
    )


# ============================================================================
# PREPARE APPLICATION MATERIALS
# ============================================================================

def prepare_application(job: Job, profile: Profile) -> Dict:
    """
    Prepare application materials for human review.

    CRITICAL: Resume stays local. Nothing is transmitted to job boards.
    All materials are returned for human review + approval.
    """
    logger.info(f"Preparing application for: {job.company} - {job.title}")
    audit_log(
        "PREPARE_STARTED",
        job_id=job.job_id,
        company=job.company,
        title=job.title,
        resume_included=False,
        contact_info_included=False,
    )

    jd_skills = extract_skills_advanced(f"{job.title} {job.description}")

    # Tailored resume bullets
    resume_bullets = []
    if jd_skills:
        top_skills = jd_skills[:5]
        resume_bullets.append(
            f"Demonstrated proficiency with {', '.join(top_skills)} "
            f"supporting 60+ enterprise customers in MSSP operations."
        )
    resume_bullets.extend([
        "Contributed to 50% MTTR reduction through SOC automation (PurpleLens) "
        "integrated with Swimlane SOAR.",
        "Experience with cross-platform EDR/SIEM operations across 3,000+ endpoints "
        "in US, APAC, and EU regions.",
        f"[HUMAN: Add 1-2 bullets specific to {job.company}'s tech stack]",
    ])

    # Cover letter draft
    skills_str = ", ".join(jd_skills[:3]) if jd_skills else "security operations"
    cover_letter = f"""Dear Hiring Manager at {job.company},

I am writing to express my interest in the {job.title} position. With hands-on \
experience in {skills_str} supporting 60+ enterprise customers as a Cybersecurity \
Analyst II at 11:11 Systems, I am confident I can contribute effectively to your team.

My strongest example is PurpleLens, a SOC investigation automation tool I helped \
operationalize within our Swimlane SOAR workflow, contributing to a 50% reduction in \
mean time to resolution. I bring security operations depth, API-based troubleshooting, \
and hands-on automation experience.

[HUMAN: Edit this paragraph — why specifically {job.company}? Their mission, culture, \
tech stack, recent news?]

I hold multiple industry certifications including GSEC, GCIH, GCIA, Security+, CySA+, \
and SSCP, along with a postgraduate credential in AI/ML Engineering from UT Austin.

I would welcome the opportunity to discuss how my experience aligns with your team's \
needs. Thank you for your consideration.

Best regards,
{profile.full_name}
"""

    # Pre-fill screening answers
    common_answers = {
        "years_experience": "3+ years in cybersecurity operations (SOC, IR, endpoint security)",
        "why_this_company": f"[HUMAN: Why {job.company}? Research their mission, tech stack, team]",
        "why_this_role": f"[HUMAN: Why {job.title}? How it aligns with your career goals]",
        "biggest_achievement": "Helped operationalize PurpleLens SOC automation tool, "
                               "contributing to 50% MTTR reduction across 60+ enterprise clients.",
        "salary_expectations": f"[HUMAN: Research {job.company}'s range. Current: {job.salary_range or 'Not listed'}]",
        "work_authorization": "Authorized to work in the US",
        "availability": "[HUMAN: Your start date availability]",
    }

    human_review_checklist = [
        "[ ] Verify resume bullets are accurate for this specific role",
        "[ ] Edit cover letter with company-specific reasons",
        "[ ] Fill in [HUMAN:] placeholders with your own examples",
        f"[ ] Confirm skill alignment: {', '.join(jd_skills[:5])}",
        "[ ] Review salary expectations",
        "[ ] Proofread for typos and grammar",
        f"[ ] Visit application URL: {job.url}",
    ]

    materials = {
        "job_id": job.job_id,
        "timestamp": datetime.now().isoformat(),
        "company": job.company,
        "title": job.title,
        "url": job.url,
        "source": job.source,
        "resume_bullets": resume_bullets,
        "cover_letter_draft": cover_letter,
        "common_answers": common_answers,
        "human_review_checklist": human_review_checklist,
        "data_security": {
            "resume_sent_to_board": False,
            "contact_info_sent": False,
            "personal_data_transmitted": False,
            "all_data_local": True,
        },
    }

    audit_log(
        "PREPARE_COMPLETED",
        job_id=job.job_id,
        materials_count=3,
        human_review_required=True,
        resume_transmitted=False,
    )

    return materials


# ============================================================================
# SUBMIT WITH HUMAN APPROVAL GATE
# ============================================================================

def generate_confirmation_code(job_id: str, prepared_materials: Dict) -> str:
    """Generate confirmation code. User must enter this to approve submission."""
    content = f"{job_id}:{prepared_materials['timestamp']}".encode()
    code = hashlib.sha256(content).hexdigest()[:8].upper()
    return code


def submit_manual(
    job_id: str,
    prepared_materials: Dict,
    confirmation_code: str,
    profile: Profile,
) -> Dict:
    """
    Manual submission: Human approves, agent assists.

    CRITICAL: Confirmation code proves human reviewed materials.
    No automatic submission is possible.
    """
    expected_code = generate_confirmation_code(job_id, prepared_materials)
    if confirmation_code.upper() != expected_code:
        audit_log(
            "SUBMIT_FAILED",
            job_id=job_id,
            reason="invalid_confirmation_code",
        )
        raise PermissionError(
            f"Invalid confirmation code. Expected: {expected_code}. "
            f"Did you review the materials first?"
        )

    logger.info(f"Submitting application for job {job_id} (human-approved)")
    audit_log("SUBMIT_APPROVED", job_id=job_id, human_approved=True)

    result = {
        "job_id": job_id,
        "status": "ready_to_submit",
        "timestamp": datetime.now().isoformat(),
        "confirmation_code": confirmation_code,
        "next_step": f"Apply at: {prepared_materials.get('url', 'N/A')}",
    }

    track_opportunity(job_id, prepared_materials, "approved", "Human-approved via job-search-custom")
    return result


def track_opportunity(job_id: str, materials: Dict, status: str, notes: str = ""):
    """Track opportunity in persistent log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        "company": materials.get("company"),
        "title": materials.get("title"),
        "url": materials.get("url"),
        "source": materials.get("source"),
        "status": status,
        "notes": notes,
    }

    if os.path.exists(OPPORTUNITIES_LOG):
        with open(OPPORTUNITIES_LOG, "r") as f:
            opportunities = json.load(f)
    else:
        opportunities = []

    opportunities.append(entry)
    with open(OPPORTUNITIES_LOG, "w") as f:
        json.dump(opportunities, f, indent=2)

    audit_log("TRACK_OPPORTUNITY", job_id=job_id, status=status)


# ============================================================================
# DAILY DIGEST
# ============================================================================

def run_daily_digest(
    sites: Optional[List[str]] = None,
    budget_limit: int = 50,
    min_score: float = MIN_SCORE_THRESHOLD,
) -> Dict:
    """
    Run a full daily digest: search all sites with combined queries,
    score against profile, and produce a summary report.

    Designed to be called by cron. Output goes to daily_digest.json.

    Credit budget strategy:
    - 3 combined query groups × N sites
    - LinkedIn (1 credit) + Indeed (4) + Monster (4) + Dice (4)
      + CyberSecJobs (1) + InfoSecJobs (1) + SimplyHired (4) + USAJobs (4)
    - Total per query: ~23 credits
    - 3 queries × 23 = ~69 credits max (usually less due to budget cap)
    """
    profile = load_profile()
    locations = profile.target_locations

    # Use first non-"Remote" location, or "Remote" if that's all we have
    primary_location = next(
        (loc for loc in locations if loc.lower() != "remote"),
        locations[0] if locations else "Seattle, WA"
    )

    all_jobs = []
    total_credits = 0

    for query_group in QUERY_GROUPS:
        if budget_limit and total_credits >= budget_limit:
            logger.info(f"Daily digest budget reached: {total_credits}/{budget_limit}")
            break

        remaining_budget = budget_limit - total_credits if budget_limit else None
        jobs = search_all_sites(
            query=query_group,
            location=primary_location,
            sites=sites,
            max_results_per_site=10,
            budget_limit=remaining_budget,
        )
        all_jobs.extend(jobs)
        total_credits = rate_limiter.oxylabs_quota_used

    # Deduplicate across all query groups
    all_jobs = _deduplicate_jobs(all_jobs)

    # Score all jobs
    scored = [score_job(job, profile) for job in all_jobs]
    scored.sort(key=lambda s: s.score, reverse=True)

    # Filter by min score
    strong = [s for s in scored if s.recommendation == "STRONG_MATCH"]
    good = [s for s in scored if s.recommendation == "GOOD_MATCH"]
    moderate = [s for s in scored if s.recommendation == "MODERATE_MATCH"]
    weak = [s for s in scored if s.score >= min_score and s.recommendation == "WEAK_MATCH"]

    digest = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_found": len(all_jobs),
            "strong_matches": len(strong),
            "good_matches": len(good),
            "moderate_matches": len(moderate),
            "weak_above_threshold": len(weak),
            "credits_used_today": total_credits,
            "credits_remaining": rate_limiter.get_remaining(),
        },
        "top_matches": [
            {
                "title": s.job.title,
                "company": s.job.company,
                "location": s.job.location,
                "source": s.job.source,
                "url": s.job.url,
                "score": s.score,
                "recommendation": s.recommendation,
                "matched_skills": s.matched_skills[:5],
                "missing_skills": s.missing_skills[:3],
                "matched_certs": s.matched_certs,
                "title_match": s.title_match,
                "salary": s.job.salary_range,
                "posted": s.job.posted_date,
            }
            for s in (strong + good + moderate + weak)[:25]  # Top 25
        ],
        "query_groups_used": QUERY_GROUPS,
        "sites_enabled": [k for k, v in SITE_CONFIGS.items() if v.get("enabled")],
        "location": primary_location,
    }

    # Save digest
    with open(DIGEST_OUTPUT, "w") as f:
        json.dump(digest, f, indent=2)

    # Also save per-date archive
    archive_dir = SKILL_DIR / "digests"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f"digest_{digest['date']}.json"
    with open(archive_path, "w") as f:
        json.dump(digest, f, indent=2)

    logger.info(
        f"Daily digest complete: {len(all_jobs)} jobs found, "
        f"{len(strong)} strong + {len(good)} good + {len(moderate)} moderate matches"
    )

    return digest


def format_digest_telegram(digest: Dict) -> str:
    """Format a digest as a Telegram-friendly message."""
    s = digest["summary"]
    lines = [
        f"📋 **Job Search Digest — {digest['date']}**",
        f"",
        f"🔍 Found **{s['total_found']}** jobs across {len(digest['sites_enabled'])} sites",
        f"🟢 Strong: **{s['strong_matches']}** | 🔵 Good: **{s['good_matches']}** | "
        f"🟡 Moderate: **{s['moderate_matches']}**",
        f"💰 Credits used: {s['credits_used_today']} | Remaining: {s['credits_remaining']}",
        f"",
    ]

    for i, match in enumerate(digest["top_matches"][:15], 1):
        emoji = {"STRONG_MATCH": "🟢", "GOOD_MATCH": "🔵", "MODERATE_MATCH": "🟡"}.get(
            match["recommendation"], "⚪"
        )
        title_flag = " 🎯" if match["title_match"] else ""
        salary = f" | {match['salary']}" if match.get("salary") else ""
        lines.append(
            f"{emoji} **{i}. {match['title']}** @ {match['company']}{title_flag}"
        )
        lines.append(
            f"   📍 {match['location']} | {match['source'].capitalize()}{salary}"
        )
        lines.append(
            f"   Score: {match['score']:.0%} | Skills: {', '.join(match['matched_skills'][:3])}"
        )
        if match.get("url"):
            lines.append(f"   🔗 {match['url']}")
        lines.append("")

    lines.append("Use `prepare --job-id <ID>` to generate application materials.")
    return "\n".join(lines)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Secure job search: search, score, prepare, submit (human-approved)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # --- search ---
    search_parser = subparsers.add_parser("search", help="Search for jobs")
    search_parser.add_argument("--query", required=True, help="Job title or keywords (supports OR)")
    search_parser.add_argument(
        "--location", "--locations", dest="locations", required=True,
        help="Location or locations (comma-separated)"
    )
    search_parser.add_argument("--max-results", type=int, default=10, help="Max results per site")
    search_parser.add_argument("--output", help="Save results to JSON file")
    search_parser.add_argument(
        "--sites", help="Comma-separated site keys (default: linkedin). "
                        "Use 'all' for all enabled sites."
    )
    search_parser.add_argument("--budget", type=int, help="Max credits to spend")

    # --- score ---
    score_parser = subparsers.add_parser("score", help="Score jobs against resume/profile")
    score_parser.add_argument("--jobs", required=True, help="JSON file with jobs")
    score_parser.add_argument("--profile", help="Profile JSON file (default: auto-detect)")
    score_parser.add_argument("--min-score", type=float, default=MIN_SCORE_THRESHOLD)
    score_parser.add_argument("--output", help="Save scored results to JSON file")

    # --- prepare ---
    prepare_parser = subparsers.add_parser("prepare", help="Prepare application materials")
    prepare_parser.add_argument("--job-id", required=True, help="Job ID from search results")
    prepare_parser.add_argument("--job-file", required=True, help="JSON file with job details")
    prepare_parser.add_argument("--profile", help="Profile JSON file (default: auto-detect)")
    prepare_parser.add_argument("--output", required=True, help="Output file for materials")

    # --- submit ---
    submit_parser = subparsers.add_parser("submit", help="Submit application (human-approved)")
    submit_parser.add_argument("--prepared", required=True, help="Prepared materials JSON file")
    submit_parser.add_argument("--confirmation-code", required=True, help="Confirmation code")
    submit_parser.add_argument("--profile", help="Profile JSON file")

    # --- digest ---
    digest_parser = subparsers.add_parser("digest", help="Run daily digest across all sites")
    digest_parser.add_argument("--budget", type=int, default=50, help="Max credits (default 50)")
    digest_parser.add_argument("--min-score", type=float, default=MIN_SCORE_THRESHOLD)
    digest_parser.add_argument("--sites", help="Comma-separated site keys (default: all)")
    digest_parser.add_argument("--format", choices=["json", "telegram"], default="json")

    # --- track ---
    track_parser = subparsers.add_parser("track", help="Track opportunity status")
    track_parser.add_argument("--job-id", required=True, help="Job ID")
    track_parser.add_argument("--status", required=True, help="Status")
    track_parser.add_argument("--notes", default="", help="Optional notes")

    # --- quota ---
    subparsers.add_parser("quota", help="Show current credit quota status")

    # --- sites ---
    subparsers.add_parser("sites", help="List available job sites and their status")

    # Parse
    args = parser.parse_args()
    setup_logging()

    if not args.command:
        parser.print_help()
        return

    # ── search ──
    if args.command == "search":
        locations = [l.strip() for l in args.locations.split(",")]
        location_str = locations[0]

        if args.sites:
            if args.sites.lower() == "all":
                site_keys = None  # search_all_sites defaults to all
            else:
                site_keys = [s.strip() for s in args.sites.split(",")]
        else:
            site_keys = ["linkedin"]  # Default to LinkedIn (cheapest)

        if site_keys and len(site_keys) == 1:
            jobs = search_site(site_keys[0], args.query, location_str, args.max_results)
        else:
            jobs = search_all_sites(
                args.query, location_str,
                sites=site_keys,
                max_results_per_site=args.max_results,
                budget_limit=args.budget,
            )

        if args.output:
            with open(args.output, "w") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2)
            logger.info(f"Saved {len(jobs)} jobs to {args.output}")
        else:
            for job in jobs:
                print(f"[{job.source}] {job.title} at {job.company} ({job.location})")
                if job.url:
                    print(f"  → {job.url}")
            print(f"\nTotal: {len(jobs)} jobs found")

    # ── score ──
    elif args.command == "score":
        profile = load_profile(args.profile)

        with open(args.jobs, "r") as f:
            jobs_data = json.load(f)
        jobs = [Job(**j) for j in jobs_data]

        scored = [score_job(job, profile) for job in jobs]
        scored.sort(key=lambda s: s.score, reverse=True)

        # Filter and display
        filtered = [s for s in scored if s.score >= args.min_score]
        for s in filtered:
            emoji = {"STRONG_MATCH": "🟢", "GOOD_MATCH": "🔵",
                     "MODERATE_MATCH": "🟡", "WEAK_MATCH": "⚪"}[s.recommendation]
            print(f"{emoji} [{s.score:.0%}] {s.job.title} at {s.job.company}")
            print(f"  Skills: {', '.join(s.matched_skills[:5])}")
            if s.missing_skills:
                print(f"  Missing: {', '.join(s.missing_skills[:3])}")
            if s.matched_certs:
                print(f"  Certs: {', '.join(s.matched_certs)}")
            print(f"  Title match: {'Yes 🎯' if s.title_match else 'No'}")
            print()

        print(f"Showing {len(filtered)}/{len(scored)} jobs above {args.min_score:.0%} threshold")

        if args.output:
            output_data = [
                {**asdict(s.job), "score": s.score, "recommendation": s.recommendation,
                 "matched_skills": s.matched_skills, "missing_skills": s.missing_skills,
                 "matched_certs": s.matched_certs, "title_match": s.title_match}
                for s in filtered
            ]
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Saved {len(filtered)} scored jobs to {args.output}")

    # ── prepare ──
    elif args.command == "prepare":
        profile = load_profile(args.profile)

        with open(args.job_file, "r") as f:
            jobs_data = json.load(f)

        # Find the specific job by ID
        target_job = None
        for j in jobs_data:
            if j.get("job_id") == args.job_id:
                target_job = Job(**j)
                break

        if not target_job:
            logger.error(f"Job ID '{args.job_id}' not found in {args.job_file}")
            sys.exit(1)

        materials = prepare_application(target_job, profile)

        with open(args.output, "w") as f:
            json.dump(materials, f, indent=2)
        logger.info(f"Application materials saved to {args.output}")

        # Show confirmation code
        code = generate_confirmation_code(args.job_id, materials)
        print(f"\n✅ Materials prepared for: {target_job.title} at {target_job.company}")
        print(f"📄 Output: {args.output}")
        print(f"🔑 Confirmation code (for submit): {code}")
        print(f"⚠️  Review all [HUMAN:] sections before submitting!")

    # ── submit ──
    elif args.command == "submit":
        profile = load_profile(args.profile)

        with open(args.prepared, "r") as f:
            materials = json.load(f)

        job_id = materials.get("job_id")
        result = submit_manual(job_id, materials, args.confirmation_code, profile)

        print(f"\n✅ Application approved: {materials['title']} at {materials['company']}")
        print(f"🔗 Apply here: {result['next_step']}")
        print(f"Status: {result['status']}")

    # ── digest ──
    elif args.command == "digest":
        sites = [s.strip() for s in args.sites.split(",")] if args.sites else None
        digest = run_daily_digest(
            sites=sites,
            budget_limit=args.budget,
            min_score=args.min_score,
        )

        if args.format == "telegram":
            print(format_digest_telegram(digest))
        else:
            print(json.dumps(digest, indent=2))

    # ── track ──
    elif args.command == "track":
        track_opportunity(args.job_id, {}, args.status, args.notes)
        logger.info(f"Tracked: {args.job_id} -> {args.status}")

    # ── quota ──
    elif args.command == "quota":
        remaining = rate_limiter.get_remaining()
        print(f"Oxylabs Credit Quota:")
        print(f"  Used:      {rate_limiter.oxylabs_quota_used}")
        print(f"  Total:     {rate_limiter.oxylabs_quota_total}")
        print(f"  Remaining: {remaining}")
        print(f"  Month:     {rate_limiter._month}")

    # ── sites ──
    elif args.command == "sites":
        print("Available Job Sites:")
        print(f"{'Key':<15} {'Name':<20} {'JS?':<5} {'Credits':<8} {'Status'}")
        print("-" * 60)
        for key, config in SITE_CONFIGS.items():
            status = "✅ Enabled" if config.get("enabled") else "❌ Disabled"
            js = "Yes" if config["needs_js"] else "No"
            print(f"{key:<15} {config['name']:<20} {js:<5} {config['credits_per_page']:<8} {status}")

    else:
        logger.warning(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
