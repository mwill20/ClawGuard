#!/usr/bin/env python3
"""
job-search-custom v2: Persistent job search pipeline for OpenClaw.

One-stop-shop: searches 8 job boards on a staggered schedule, deduplicates
across runs via SQLite, scores against resume/profile, auto-prepares tailored
materials (resume + cover letter) for STRONG/GOOD matches, and notifies via
Telegram + email.

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
import sqlite3
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from urllib.parse import quote_plus, urlencode

# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_FILE = "job_search_audit.log"
RATE_LIMIT_SECONDS = 5
MAX_RESULTS_PER_SEARCH = 50
MIN_SCORE_THRESHOLD = 0.40
AUTO_PREPARE_THRESHOLD = 0.60  # Auto-prepare materials for STRONG + GOOD matches
ENRICHMENT_DAILY_CAP = 30     # Max JD enrichments per day (budget control)

# Persistent data directory (Docker volume-mounted at /data/)
DATA_DIR = Path(os.getenv("CLAWGUARD_DATA_DIR", "/data/clawguard"))
DB_PATH = DATA_DIR / "jobs.db"
APPLICATIONS_DIR = DATA_DIR / "applications"
LOGS_DIR = DATA_DIR / "logs"
DIGESTS_DIR = DATA_DIR / "digests"

# API Configuration
OXYLABS_API_KEY = os.getenv("OXYLABS_AISTUDIO_API_KEY", "")

# Skill base directory (where this script lives)
SKILL_DIR = Path(__file__).parent.resolve()
TAILORING_RULES_PATH = DATA_DIR / "tailoring_rules.json"
TAILORING_RULES_DEFAULT = SKILL_DIR / "tailoring_rules.json"

# Email configuration (Gmail SMTP with TLS)
EMAIL_FROM = os.getenv("CLAWGUARD_EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("CLAWGUARD_EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("CLAWGUARD_EMAIL_TO", "mwill.itmission@gmail.com")
EMAIL_SMTP_HOST = os.getenv("CLAWGUARD_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("CLAWGUARD_SMTP_PORT", "587"))

# ============================================================================
# SITE CONFIGURATIONS
# ============================================================================

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
    },
    "remotehunter": {
        "name": "RemoteHunter",
        "url_builder": lambda q, loc: (
            f"https://www.remotehunter.com/jobs"
            f"?query={quote_plus(q)}&location={quote_plus(loc)}"
        ),
        "needs_js": True,
        "credits_per_page": 4,
        "enabled": True,
    },
}

# Credit-efficient combined query groups
QUERY_GROUPS = [
    "SOC Analyst OR SOC Engineer OR Security Operations Engineer",
    "Security Engineer OR Detection Engineer OR AI Security Engineer",
    "Threat Hunter OR Customer Success Engineer cybersecurity",
]

# ============================================================================
# LOGGING & AUDIT
# ============================================================================

def setup_logging():
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
    job_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    salary_range: Optional[str] = None

@dataclass
class Profile:
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
    job: Job
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    matched_certs: List[str]
    title_match: bool
    recommendation: str

# ============================================================================
# SQLITE JOB DATABASE
# ============================================================================

class JobDatabase:
    """Persistent job database with cross-run deduplication and lifecycle tracking."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()

    def _ensure_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id          TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                company         TEXT NOT NULL,
                location        TEXT,
                description     TEXT,
                url             TEXT,
                source          TEXT,
                posted_date     TEXT,
                salary_range    TEXT,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                dedup_key       TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'found',
                score           REAL,
                recommendation  TEXT,
                matched_skills  TEXT,
                missing_skills  TEXT,
                matched_certs   TEXT,
                title_match     INTEGER DEFAULT 0,
                materials_dir   TEXT,
                notes           TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_dedup_key ON jobs(dedup_key);
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen);
            CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);

            CREATE TABLE IF NOT EXISTS job_status_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      TEXT NOT NULL REFERENCES jobs(job_id),
                old_status  TEXT,
                new_status  TEXT NOT NULL,
                changed_at  TEXT NOT NULL DEFAULT (datetime('now')),
                changed_by  TEXT DEFAULT 'system',
                notes       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_history_job_id ON job_status_history(job_id);

            CREATE TABLE IF NOT EXISTS search_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id          TEXT NOT NULL,
                site            TEXT NOT NULL,
                query           TEXT NOT NULL,
                location        TEXT,
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                jobs_found      INTEGER DEFAULT 0,
                new_jobs        INTEGER DEFAULT 0,
                credits_used    INTEGER DEFAULT 0,
                error           TEXT
            );

            CREATE TABLE IF NOT EXISTS quota (
                month       TEXT PRIMARY KEY,
                used        INTEGER DEFAULT 0,
                total       INTEGER DEFAULT 1000,
                last_updated TEXT
            );
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Deduplication ──

    @staticmethod
    def make_dedup_key(title: str, company: str) -> str:
        t = re.sub(r'[^a-z0-9]', '', title.lower())
        c = re.sub(r'[^a-z0-9]', '', company.lower())
        return f"{t}|{c}"

    def is_known(self, dedup_key: str) -> Optional[str]:
        """Return job_id if this dedup_key exists, else None."""
        row = self.conn.execute(
            "SELECT job_id FROM jobs WHERE dedup_key = ?", (dedup_key,)
        ).fetchone()
        return row["job_id"] if row else None

    def is_known_by_id(self, job_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None

    # ── Job CRUD ──

    def upsert_job(self, job: Job) -> bool:
        """Insert new job or update last_seen. Returns True if new."""
        now = datetime.now().isoformat()
        dedup_key = self.make_dedup_key(job.title, job.company)
        existing_id = self.is_known(dedup_key)

        if existing_id:
            self.conn.execute(
                "UPDATE jobs SET last_seen = ?, updated_at = ? WHERE job_id = ?",
                (now, now, existing_id)
            )
            self.conn.commit()
            return False  # Not new
        else:
            self.conn.execute("""
                INSERT INTO jobs (job_id, title, company, location, description,
                    url, source, posted_date, salary_range,
                    first_seen, last_seen, dedup_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.title, job.company, job.location, job.description,
                job.url, job.source, job.posted_date, job.salary_range,
                now, now, dedup_key
            ))
            self.conn.execute("""
                INSERT INTO job_status_history (job_id, new_status, changed_by)
                VALUES (?, 'found', 'system')
            """, (job.job_id,))
            self.conn.commit()
            return True  # New job

    def get_job(self, job_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = ? ORDER BY score DESC NULLS LAST, first_seen DESC LIMIT ?",
            (status, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_new_jobs_since(self, since_iso: str) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE first_seen >= ? ORDER BY score DESC NULLS LAST",
            (since_iso,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_todays_new_jobs(self) -> List[dict]:
        today = datetime.now().strftime("%Y-%m-%dT00:00:00")
        return self.get_new_jobs_since(today)

    def get_earliest_first_seen(self) -> Optional[str]:
        row = self.conn.execute("SELECT MIN(first_seen) as earliest FROM jobs").fetchone()
        return row["earliest"] if row else None

    def is_first_week(self) -> bool:
        """
        Check if the pipeline is in its first week of operation.
        During the first week, we show all found jobs (catch-up mode).
        After the first week, we only show jobs from the last 24 hours.
        """
        earliest = self.get_earliest_first_seen()
        if not earliest:
            return True  # No jobs yet = first run
        try:
            first_date = datetime.fromisoformat(earliest)
            days_since = (datetime.now() - first_date).days
            return days_since < 7
        except (ValueError, TypeError):
            return True

    def get_digest_jobs(self) -> List[dict]:
        """
        Get jobs for today's digest with smart date filtering:
        - First week: all jobs in DB (catch-up mode)
        - After first week: only jobs first_seen in last 24 hours
        """
        if self.is_first_week():
            logger.info("First-week mode: including all jobs in digest")
            rows = self.conn.execute(
                "SELECT * FROM jobs ORDER BY score DESC NULLS LAST, first_seen DESC"
            ).fetchall()
        else:
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            logger.info(f"Daily mode: jobs since {cutoff}")
            rows = self.conn.execute(
                "SELECT * FROM jobs WHERE first_seen >= ? ORDER BY score DESC NULLS LAST",
                (cutoff,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_job_count(self) -> dict:
        """Return count of jobs by status."""
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    def get_total_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
        return row["cnt"]

    # ── Status transitions ──

    def update_status(self, job_id: str, new_status: str,
                      changed_by: str = "system", notes: str = ""):
        job = self.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found in DB")
            return
        old_status = job["status"]
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
            (new_status, now, job_id)
        )
        self.conn.execute("""
            INSERT INTO job_status_history (job_id, old_status, new_status, changed_by, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, old_status, new_status, changed_by, notes))
        self.conn.commit()

    # ── Scoring persistence ──

    def update_score(self, job_id: str, scored: 'ScoredJob'):
        now = datetime.now().isoformat()
        self.conn.execute("""
            UPDATE jobs SET
                score = ?, recommendation = ?,
                matched_skills = ?, missing_skills = ?,
                matched_certs = ?, title_match = ?,
                status = CASE WHEN status = 'found' THEN 'scored' ELSE status END,
                updated_at = ?
            WHERE job_id = ?
        """, (
            scored.score, scored.recommendation,
            json.dumps(scored.matched_skills), json.dumps(scored.missing_skills),
            json.dumps(scored.matched_certs), 1 if scored.title_match else 0,
            now, job_id
        ))
        if self.conn.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,)).fetchone()["status"] == "scored":
            self.conn.execute("""
                INSERT INTO job_status_history (job_id, old_status, new_status, changed_by)
                VALUES (?, 'found', 'scored', 'system')
            """, (job_id,))
        self.conn.commit()

    def set_materials_dir(self, job_id: str, materials_dir: str):
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE jobs SET materials_dir = ?, status = 'prepared', updated_at = ? WHERE job_id = ?",
            (materials_dir, now, job_id)
        )
        self.conn.execute("""
            INSERT INTO job_status_history (job_id, old_status, new_status, changed_by)
            VALUES (?, 'scored', 'prepared', 'system')
        """, (job_id,))
        self.conn.commit()

    # ── Quota ──

    def get_quota(self) -> Tuple[int, int]:
        month = datetime.now().strftime("%Y-%m")
        row = self.conn.execute("SELECT used, total FROM quota WHERE month = ?", (month,)).fetchone()
        if row:
            return row["used"], row["total"]
        self.conn.execute(
            "INSERT INTO quota (month, used, total, last_updated) VALUES (?, 0, 1000, ?)",
            (month, datetime.now().isoformat())
        )
        self.conn.commit()
        return 0, 1000

    def track_usage(self, credits: int):
        month = datetime.now().strftime("%Y-%m")
        used, total = self.get_quota()
        new_used = used + credits
        self.conn.execute(
            "INSERT OR REPLACE INTO quota (month, used, total, last_updated) VALUES (?, ?, ?, ?)",
            (month, new_used, total, datetime.now().isoformat())
        )
        self.conn.commit()
        logger.info(f"Quota: {new_used}/{total} used. Remaining: {total - new_used}")

    def get_remaining_credits(self) -> int:
        used, total = self.get_quota()
        return total - used

    def get_todays_enrichment_count(self) -> int:
        """Count how many JD enrichments have been done today."""
        today = datetime.now().strftime("%Y-%m-%d")
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM search_runs WHERE site = 'enrichment' AND started_at LIKE ?",
            (f"{today}%",)
        ).fetchone()
        return row["cnt"] if row else 0

    def get_unenriched_jobs(self, limit: int = 100) -> List[dict]:
        """Get jobs with thin descriptions (<200 chars), ordered by score + title_match."""
        rows = self.conn.execute("""
            SELECT * FROM jobs
            WHERE (description IS NULL OR length(description) < 200)
              AND url IS NOT NULL AND url != ''
            ORDER BY title_match DESC, score DESC NULLS LAST, first_seen DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ── Search runs ──

    def record_search_run(self, run_id: str, site: str, query: str, location: str,
                          jobs_found: int, new_jobs: int, credits_used: int, error: str = ""):
        self.conn.execute("""
            INSERT INTO search_runs (run_id, site, query, location, started_at, completed_at,
                jobs_found, new_jobs, credits_used, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, site, query, location,
            datetime.now().isoformat(), datetime.now().isoformat(),
            jobs_found, new_jobs, credits_used, error
        ))
        self.conn.commit()


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    def __init__(self, db: JobDatabase, min_interval: int = RATE_LIMIT_SECONDS):
        self.db = db
        self.last_search_time = 0
        self.min_interval = min_interval

    def check_rate_limit(self):
        elapsed = time.time() - self.last_search_time
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.info(f"Rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        self.last_search_time = time.time()

    def check_quota(self, estimated_cost: int):
        remaining = self.db.get_remaining_credits()
        if estimated_cost > remaining:
            raise RuntimeError(
                f"Oxylabs quota low. Remaining: {remaining}. "
                f"Estimated cost: {estimated_cost}"
            )


# ============================================================================
# TAILORING ENGINE
# ============================================================================

class TailoringEngine:
    """Rule-governed resume tailoring — no fabrication, no embellishment."""

    DEFAULT_RULES = {
        "version": 1,
        "rules": {
            "no_fabrication": "Only claim skills and experience present in resume.txt",
            "no_embellishment": "Do not exaggerate metrics, scope, or seniority",
            "base_on_resume": "All tailored bullets must derive from resume.txt",
            "highlight_relevant": "Reorder to emphasize JD-matching experience",
            "preserve_metrics": "Use actual metrics only",
            "human_placeholders": "Mark anything requiring judgment with [HUMAN:]",
        },
        "allowed_metrics": [
            "50% MTTR reduction",
            "60+ enterprise customers",
            "3,000+ endpoints",
            "300+ events weekly",
            "30+ member team",
            "25+ requests per week",
            "30+ incidents per month",
            "57 adversarial test cases",
            "1,000+ endpoints",
        ],
        "bullet_templates": [
            {
                "template": "Manage endpoint security operations across {endpoints} systems in {regions}, triaging {events} events weekly while supporting {customers} enterprise customers.",
                "source": "Cybersecurity Analyst II | 11:11 Systems",
                "keywords": ["edr", "endpoint", "siem", "soc", "security operations", "triage"],
                "variables": {"endpoints": "3,000+", "regions": "US, APAC, and EU", "events": "300+", "customers": "60+"},
            },
            {
                "template": "Contributed to {reduction} MTTR reduction by operationalizing {tool} within {platform}, reducing manual investigation prep across {customers} enterprise clients.",
                "source": "PurpleLens | SOC Investigation Automation",
                "keywords": ["soar", "automation", "incident response", "mttr", "soc", "investigation"],
                "variables": {"reduction": "50%", "tool": "PurpleLens SOC automation", "platform": "Swimlane SOAR", "customers": "60+"},
            },
            {
                "template": "Build and validate integrations across EDR, SIEM, and Threat Intel feeds using Postman and API testing to verify authentication, response structure, and production readiness.",
                "source": "Cybersecurity Analyst II | 11:11 Systems",
                "keywords": ["api", "rest", "integration", "postman", "siem", "edr", "threat intel"],
                "variables": {},
            },
            {
                "template": "Investigate {incidents} incident response investigations per month, translating findings into clear, actionable reports and guidance for customers.",
                "source": "Cybersecurity Analyst II | 11:11 Systems",
                "keywords": ["incident response", "ir", "forensics", "investigation", "reporting"],
                "variables": {"incidents": "30+"},
            },
            {
                "template": "Customer success engineering: onboard environments, troubleshoot telemetry, tune detections, and coordinate containment including evidence preservation.",
                "source": "Cybersecurity Analyst II | 11:11 Systems",
                "keywords": ["customer success", "onboarding", "customer facing", "telemetry", "containment"],
                "variables": {},
            },
            {
                "template": "Built production SOC architecture standing up tooling across BitDefender, Wazuh, Splunk, TheHive, Action1, and Software Defined Perimeter.",
                "source": "Director of Cybersecurity | CDIC",
                "keywords": ["soc", "architecture", "splunk", "wazuh", "security engineering", "detection engineering"],
                "variables": {},
            },
            {
                "template": "Led a {team_size} member team spanning SOC, security engineering, incident response, and GRC support.",
                "source": "Director of Cybersecurity | CDIC",
                "keywords": ["leadership", "team lead", "management", "soc", "security engineering"],
                "variables": {"team_size": "30+"},
            },
            {
                "template": "Built secure code analysis platform using deterministic controls and LLM-assisted reasoning to detect unsafe patterns, validated across {tests} adversarial test cases.",
                "source": "AI DevSecOps Platform",
                "keywords": ["devsecops", "ai", "llm", "ml", "code analysis", "ai security", "mlsecops"],
                "variables": {"tests": "57"},
            },
            {
                "template": "Postgraduate credential in AI/ML Engineering from UT Austin (McCombs), with applied experience in agentic AI, LLM deployment, and MLSecOps.",
                "source": "Education",
                "keywords": ["ai", "ml", "machine learning", "llm", "ai security", "data science"],
                "variables": {},
            },
        ],
    }

    def __init__(self, resume_text: str, rules_path: Optional[Path] = None):
        self.resume_text = resume_text
        self.resume_lower = resume_text.lower()

        if rules_path and rules_path.exists():
            with open(rules_path, "r") as f:
                self.rules = json.load(f)
        else:
            self.rules = self.DEFAULT_RULES

    def select_bullets(self, jd_skills: List[str], max_bullets: int = 5) -> List[str]:
        """Select the most relevant pre-approved bullets for this JD."""
        jd_lower = {s.lower() for s in jd_skills}
        scored_templates = []

        for tmpl in self.rules.get("bullet_templates", []):
            keywords = {k.lower() for k in tmpl.get("keywords", [])}
            overlap = len(keywords & jd_lower)
            if overlap > 0:
                # Fill in template variables
                text = tmpl["template"]
                for var, val in tmpl.get("variables", {}).items():
                    text = text.replace(f"{{{var}}}", val)
                scored_templates.append((overlap, text, tmpl["source"]))

        scored_templates.sort(key=lambda x: x[0], reverse=True)
        bullets = []
        for _, text, source in scored_templates[:max_bullets]:
            bullets.append(text)

        if not bullets:
            # Fallback: generic top bullets from resume
            bullets = [
                "Cybersecurity Analyst II supporting 60+ enterprise customers across 3,000+ endpoints in global MSSP operations.",
                "Contributed to 50% MTTR reduction through PurpleLens SOC automation integrated with Swimlane SOAR.",
            ]

        bullets.append(f"[HUMAN: Add 1-2 bullets specific to this company's tech stack and culture]")
        return bullets

    def generate_cover_letter(self, job: Job, profile: Profile, jd_skills: List[str]) -> str:
        """Generate cover letter using only verified claims from resume."""
        # Select top 3 matching skills to mention
        skills_str = ", ".join(jd_skills[:3]) if jd_skills else "security operations"

        # Pick best bullet for the body
        bullets = self.select_bullets(jd_skills, max_bullets=2)
        experience_paragraph = " ".join(bullets[:2]) if bullets else ""

        letter = f"""Dear Hiring Manager at {job.company},

I am writing to express my interest in the {job.title} position. With hands-on experience in {skills_str} supporting 60+ enterprise customers as a Cybersecurity Analyst II at 11:11 Systems, I am confident I can contribute effectively to your team.

{experience_paragraph}

[HUMAN: Why specifically {job.company}? Research their mission, culture, tech stack, and recent news. This paragraph should be entirely your own words.]

I hold multiple industry certifications including GSEC, GCIH, GCIA, Security+, CySA+, and SSCP, along with a postgraduate credential in AI/ML Engineering from UT Austin (McCombs).

I would welcome the opportunity to discuss how my experience aligns with your team's needs. Thank you for your consideration.

Best regards,
{profile.full_name}
"""
        return letter

    def validate_bullet(self, bullet: str) -> Tuple[bool, str]:
        """Check that key claims in bullet exist in resume text."""
        # Check for metrics
        metrics = re.findall(r'\d+[%+]?\s*\w+', bullet)
        for metric in metrics:
            if metric.lower() not in self.resume_lower:
                allowed = any(m.lower() in metric.lower() or metric.lower() in m.lower()
                              for m in self.rules.get("allowed_metrics", []))
                if not allowed:
                    return False, f"Metric '{metric}' not found in resume"
        return True, "OK"


# ============================================================================
# OXYLABS SEARCH ENGINE
# ============================================================================

JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "job_listings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_title":      {"type": "string"},
                    "company_name":   {"type": "string"},
                    "location":       {"type": "string"},
                    "job_detail_url": {"type": "string", "description": "Direct link to the individual job posting page (e.g. /jobs/view/...)"},
                    "apply_url":      {"type": "string", "description": "Link to apply or the job posting page"},
                    "salary":         {"type": "string"},
                    "date_posted":    {"type": "string"},
                    "description":    {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}

# Schema for scraping individual job detail pages (richer)
JOB_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "job_title":         {"type": "string"},
        "company_name":      {"type": "string"},
        "location":          {"type": "string"},
        "description":       {"type": "string"},
        "requirements":      {"type": "string"},
        "qualifications":    {"type": "string"},
        "responsibilities":  {"type": "string"},
        "salary":            {"type": "string"},
        "job_type":          {"type": "string"},
        "experience_level":  {"type": "string"},
        "apply_url":         {"type": "string"},
        "date_posted":       {"type": "string"},
    },
    "additionalProperties": False,
}

# ============================================================================
# JD ENRICHMENT — Scrape full job descriptions from detail pages
# ============================================================================

def enrich_job_description(job: Job, rate_limiter: Optional['RateLimiter'] = None,
                           db: Optional[JobDatabase] = None) -> Job:
    """
    Follow a job's URL to scrape the full job description.
    Returns updated Job with enriched description.
    Costs 1 credit (no JS) for LinkedIn, 4 credits (JS) for others.
    """
    if not job.url or not OXYLABS_API_KEY:
        return job

    # Skip if description already looks substantive (>200 chars)
    if job.description and len(job.description) > 200:
        return job

    # Determine if this URL needs JS rendering
    needs_js = True  # Default: most sites need JS
    credits = 4
    if "linkedin.com" in job.url:
        needs_js = False
        credits = 1
    elif "cybersecurityjobs.com" in job.url or "infosec-jobs.com" in job.url:
        needs_js = False
        credits = 1

    if rate_limiter:
        try:
            rate_limiter.check_quota(credits)
            rate_limiter.check_rate_limit()
        except RuntimeError:
            logger.info(f"Skipping JD enrichment for {job.job_id}: quota/rate limit")
            return job

    logger.info(f"Enriching JD for: {job.title} @ {job.company} ({job.url[:60]}...)")

    try:
        from oxylabs_ai_studio.apps.ai_scraper import AiScraper

        scraper = AiScraper(api_key=OXYLABS_API_KEY)
        result = scraper.scrape(
            url=job.url,
            output_format="json",
            schema=JOB_DETAIL_SCHEMA,
            render_javascript=needs_js,
            geo_location="US",
        )

        data = result.data if result else {}
        if data:
            # Build full description from available fields
            parts = []
            for field in ["description", "responsibilities", "requirements", "qualifications"]:
                val = data.get(field, "")
                if val and len(val.strip()) > 10:
                    parts.append(val.strip())

            if parts:
                full_desc = "\n\n".join(parts)
                job = Job(
                    job_id=job.job_id, title=job.title, company=job.company,
                    location=job.location, description=full_desc,
                    url=data.get("apply_url") or job.url,
                    source=job.source,
                    posted_date=data.get("date_posted") or job.posted_date,
                    salary_range=data.get("salary") or job.salary_range,
                )
                logger.info(f"Enriched: {len(full_desc)} chars for {job.title}")

                # Update DB if available
                if db:
                    db.conn.execute(
                        "UPDATE jobs SET description = ?, url = ?, salary_range = ?, updated_at = ? WHERE job_id = ?",
                        (job.description, job.url, job.salary_range, datetime.now().isoformat(), job.job_id)
                    )
                    db.conn.commit()

        if db:
            db.track_usage(credits)

        audit_log("JD_ENRICHED", job_id=job.job_id, chars=len(job.description or ""),
                  cost=credits)

    except Exception as e:
        logger.warning(f"JD enrichment failed for {job.job_id}: {e}")

    return job


def enrich_top_jobs(
    db: JobDatabase,
    rate_limiter: 'RateLimiter',
    daily_cap: int = ENRICHMENT_DAILY_CAP,
) -> int:
    """
    Budget-capped JD enrichment pass. Called during compile step.

    Strategy:
    1. Get unenriched jobs from DB (thin description <200 chars)
    2. Sort by title_match DESC, score DESC (best candidates first)
    3. Enrich up to daily_cap, tracking each as a 'search_run'
    4. Re-score enriched jobs with the new full JD

    Returns count of jobs enriched.
    """
    already_done = db.get_todays_enrichment_count()
    remaining_budget = daily_cap - already_done
    if remaining_budget <= 0:
        logger.info(f"Enrichment cap reached ({already_done}/{daily_cap} today)")
        return 0

    candidates = db.get_unenriched_jobs(limit=remaining_budget)
    if not candidates:
        logger.info("No unenriched jobs to process")
        return 0

    logger.info(
        f"Enrichment pass: {len(candidates)} candidates, "
        f"budget {remaining_budget}/{daily_cap} (done today: {already_done})"
    )

    enriched = 0
    for row in candidates:
        if enriched >= remaining_budget:
            break

        job = Job(
            job_id=row["job_id"], title=row["title"], company=row["company"],
            location=row["location"] or "", description=row["description"] or "",
            url=row["url"] or "", source=row["source"] or "",
            posted_date=row["posted_date"], salary_range=row["salary_range"],
        )

        updated = enrich_job_description(job, rate_limiter, db)
        if updated.description and len(updated.description) > len(job.description or ""):
            enriched += 1
            # Record as enrichment run for daily cap tracking
            db.record_search_run(
                run_id=f"enrich-{job.job_id[:8]}",
                site="enrichment",
                query=job.title,
                location=job.location,
                jobs_found=1,
                new_jobs=0,
                credits_used=1 if "linkedin" in (job.source or "") else 4,
            )

    logger.info(f"Enriched {enriched}/{len(candidates)} jobs (cap: {daily_cap}/day)")
    return enriched


def _fix_linkedin_url(raw_url: str) -> str:
    """
    Fix LinkedIn URLs: ensure we have the direct job view URL,
    not the company page or tracking-heavy redirect.

    LinkedIn job view URLs follow: linkedin.com/jobs/view/{job_id}
    """
    if not raw_url:
        return raw_url
    # Already a direct job view URL — clean up tracking params but keep it
    if "/jobs/view/" in raw_url:
        # Strip tracking parameters but keep the base URL
        base = raw_url.split("?")[0]
        return base
    # If it's a company page link, return as-is (we can't construct job URL without ID)
    return raw_url


def search_site(
    site_key: str,
    query: str,
    location: str,
    max_results: int = 10,
    db: Optional[JobDatabase] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> Tuple[List[Job], int]:
    """
    Search a specific job site. Returns (all_jobs, new_count).
    If db is provided, deduplicates against it and inserts new jobs.
    """
    config = SITE_CONFIGS.get(site_key)
    if not config or not config.get("enabled", True):
        return [], 0
    if not OXYLABS_API_KEY:
        logger.error("OXYLABS_AISTUDIO_API_KEY not set")
        return [], 0

    credits = config["credits_per_page"]
    if rate_limiter:
        rate_limiter.check_rate_limit()
        rate_limiter.check_quota(credits)

    url = config["url_builder"](query, location)
    needs_js = config["needs_js"]

    logger.info(f"Searching {config['name']}: query='{query}', location='{location}', js={needs_js}")
    audit_log("SEARCH_STARTED", method="oxylabs", site=site_key, query=query, location=location)

    run_id = str(uuid.uuid4())[:8]
    try:
        from oxylabs_ai_studio.apps.ai_scraper import AiScraper

        scraper = AiScraper(api_key=OXYLABS_API_KEY)
        result = scraper.scrape(
            url=url, output_format="json", schema=JOB_SCHEMA,
            render_javascript=needs_js, geo_location="US",
        )

        data = result.data if result else {}
        jobs = _parse_oxylabs_response(data, site_key, location, max_results)

        if db:
            db.track_usage(credits)

        # DB dedup: insert new jobs, count them
        new_count = 0
        new_jobs = []
        if db:
            for job in jobs:
                if db.upsert_job(job):
                    new_count += 1
                    new_jobs.append(job)
            db.record_search_run(run_id, site_key, query, location,
                                 len(jobs), new_count, credits)
        else:
            new_count = len(jobs)
            new_jobs = jobs

        # NOTE: JD enrichment moved to compile step (budget-capped, title-match prioritized)
        # See enrich_top_jobs() called during digest --compile

        audit_log("SEARCH_COMPLETED", site=site_key, results=len(jobs),
                  new=new_count, cost=credits)
        logger.info(f"Found {len(jobs)} jobs on {config['name']} ({new_count} new)")
        return jobs, new_count

    except Exception as e:
        logger.warning(f"{config['name']} search failed: {e}")
        audit_log("SEARCH_FAILED", site=site_key, error=str(e))
        if db:
            db.record_search_run(run_id, site_key, query, location, 0, 0, 0, str(e))
        return [], 0


def search_all_sites(
    query: str,
    location: str,
    sites: Optional[List[str]] = None,
    max_results_per_site: int = 10,
    budget_limit: Optional[int] = None,
    db: Optional[JobDatabase] = None,
    rate_limiter: Optional[RateLimiter] = None,
) -> Tuple[List[Job], int]:
    """Search multiple sites. Returns (all_jobs, total_new_count)."""
    if sites is None:
        sites = [k for k, v in SITE_CONFIGS.items() if v.get("enabled", True)]

    all_jobs = []
    total_new = 0
    credits_spent = 0

    for site_key in sites:
        config = SITE_CONFIGS.get(site_key, {})
        site_cost = config.get("credits_per_page", 4)

        if budget_limit and credits_spent + site_cost > budget_limit:
            logger.info(f"Budget limit reached ({credits_spent}/{budget_limit})")
            break

        try:
            jobs, new_count = search_site(
                site_key, query, location, max_results_per_site,
                db=db, rate_limiter=rate_limiter,
            )
            all_jobs.extend(jobs)
            total_new += new_count
            credits_spent += site_cost
        except RuntimeError as e:
            logger.warning(f"Skipping {site_key}: {e}")
        except Exception as e:
            logger.warning(f"Error searching {site_key}: {e}")

    # In-memory dedup for the returned list (DB dedup already handled)
    deduped = _deduplicate_jobs(all_jobs)
    logger.info(f"Multi-site: {len(deduped)} unique jobs, {total_new} new")
    return deduped, total_new


def _deduplicate_jobs(jobs: List[Job]) -> List[Job]:
    seen = set()
    unique = []
    for job in jobs:
        key = JobDatabase.make_dedup_key(job.title, job.company)
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _parse_oxylabs_response(data: dict, site_key: str, location: str,
                            max_results: int) -> List[Job]:
    if not data:
        return []
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
        salary  = item.get("salary") or item.get("salary_range") or item.get("compensation")
        posted  = item.get("date_posted") or item.get("posted") or item.get("date")

        # URL selection: prefer job_detail_url > apply_url > url > link
        # Then apply LinkedIn-specific cleanup
        url_candidates = [
            item.get("job_detail_url"),
            item.get("apply_url"),
            item.get("url"),
            item.get("link"),
        ]
        url = ""
        # First pass: find a /jobs/view/ URL if any exist
        for candidate in url_candidates:
            if candidate and "/jobs/view/" in str(candidate):
                url = _fix_linkedin_url(str(candidate)) if site_key == "linkedin" else str(candidate)
                break
        # Second pass: take the first non-empty URL if no /jobs/view/ found
        if not url:
            for candidate in url_candidates:
                if candidate and str(candidate).startswith("http"):
                    url = _fix_linkedin_url(str(candidate)) if site_key == "linkedin" else str(candidate)
                    break

        job_id = hashlib.md5(f"{title}{company}{url}".encode()).hexdigest()[:12]
        jobs.append(Job(
            job_id=job_id, title=str(title), company=str(company),
            location=str(loc), description=str(desc), url=str(url),
            source=site_key,
            posted_date=str(posted) if posted else None,
            salary_range=str(salary) if salary else None,
        ))
    return jobs


# Backward compat
def search_oxylabs(query: str, locations: List[str], max_results: int = 10) -> List[Job]:
    location_str = locations[0] if locations else "Remote"
    jobs, _ = search_site("linkedin", query, location_str, max_results)
    return jobs


# ============================================================================
# PROFILE LOADING
# ============================================================================

def load_profile(profile_path: Optional[str] = None) -> Profile:
    if profile_path is None:
        profile_path = str(SKILL_DIR / "job_search_profile.json")
    with open(profile_path, "r") as f:
        data = json.load(f)
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
# SKILL & CERT MATCHING
# ============================================================================

SKILL_ALIASES = {
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
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker", "container"],
    "kubernetes": ["kubernetes", "k8s"],
    "python": ["python"],
    "bash": ["bash", "shell script"],
    "powershell": ["powershell"],
    "sql": ["sql", "sqlite", "postgresql", "mysql"],
    "rest api": ["rest api", "api", "apis", "rest"],
    "git": ["git", "github", "gitlab"],
    "mitre att&ck": ["mitre att&ck", "mitre attack", "att&ck", "mitre"],
    "nist": ["nist", "nist 800"],
    "iso 27001": ["iso 27001", "iso27001"],
    "cis": ["cis benchmark", "cis controls"],
    "customer success": ["customer success", "customer facing", "client facing"],
    "documentation": ["documentation", "technical writing"],
    "communication": ["communication", "stakeholder", "reporting"],
    "llm": ["llm", "large language model", "ai/ml", "machine learning"],
    "ai security": ["ai security", "ml security", "mlsecops", "ai risk"],
}

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
    return extract_skills_advanced(text, CERT_ALIASES)


# ============================================================================
# SCORING
# ============================================================================

def score_job(job: Job, profile: Profile, db: Optional[JobDatabase] = None) -> ScoredJob:
    """Score job against profile. Optionally persist to DB."""
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
        matched_skills, missing_skills = [], []
        skill_score = 0.3

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
    if not title_match:
        title_match = any(
            all(word in title_lower for word in role.lower().split())
            for role in profile.target_roles
        )
    title_score = 1.0 if title_match else 0.2

    # 4. Resume keyword match (20%)
    resume_words = set(re.findall(r'\b\w{4,}\b', profile.resume_text.lower()))
    jd_words = set(re.findall(r'\b\w{4,}\b', jd_text))
    if jd_words:
        resume_overlap = len(resume_words & jd_words) / len(jd_words)
        resume_score = min(resume_overlap * 2, 1.0)
    else:
        resume_score = 0.3

    total = (skill_score * 0.40 + cert_score * 0.15 +
             title_score * 0.25 + resume_score * 0.20)

    if total >= 0.75:
        recommendation = "STRONG_MATCH"
    elif total >= 0.60:
        recommendation = "GOOD_MATCH"
    elif total >= 0.45:
        recommendation = "MODERATE_MATCH"
    else:
        recommendation = "WEAK_MATCH"

    scored = ScoredJob(
        job=job, score=round(total, 3),
        matched_skills=matched_skills, missing_skills=missing_skills,
        matched_certs=matched_certs, title_match=title_match,
        recommendation=recommendation,
    )

    if db:
        db.update_score(job.job_id, scored)

    return scored


# ============================================================================
# APPLICATION PREPARATION
# ============================================================================

def prepare_application(job: Job, profile: Profile,
                        tailoring: Optional[TailoringEngine] = None,
                        db: Optional[JobDatabase] = None) -> Dict:
    """Prepare application materials and save to per-job directory."""
    logger.info(f"Preparing: {job.company} — {job.title}")
    audit_log("PREPARE_STARTED", job_id=job.job_id, company=job.company, title=job.title)

    jd_skills = extract_skills_advanced(f"{job.title} {job.description}")

    if tailoring is None:
        tailoring = TailoringEngine(profile.resume_text, TAILORING_RULES_PATH)

    resume_bullets = tailoring.select_bullets(jd_skills)
    cover_letter = tailoring.generate_cover_letter(job, profile, jd_skills)

    common_answers = {
        "years_experience": "3+ years in cybersecurity operations (SOC, IR, endpoint security)",
        "why_this_company": f"[HUMAN: Why {job.company}? Research their mission, tech stack, team]",
        "why_this_role": f"[HUMAN: Why {job.title}? How it aligns with your career goals]",
        "biggest_achievement": "Helped operationalize PurpleLens SOC automation tool, contributing to 50% MTTR reduction across 60+ enterprise clients.",
        "salary_expectations": f"[HUMAN: Research {job.company}'s range. Listed: {job.salary_range or 'Not listed'}]",
        "work_authorization": "Authorized to work in the US",
        "availability": "[HUMAN: Your start date availability]",
    }

    review_checklist = [
        "[ ] Verify resume bullets are accurate for this specific role",
        "[ ] Edit cover letter — add company-specific paragraph",
        "[ ] Fill in all [HUMAN:] placeholders",
        f"[ ] Confirm skill alignment: {', '.join(jd_skills[:5])}",
        "[ ] Review salary expectations",
        "[ ] Proofread for typos and grammar",
        f"[ ] Visit application URL: {job.url}",
        "[ ] Apply and update status: track --job-id {job.job_id} --status applied",
    ]

    # Write to per-job application directory
    job_dir = APPLICATIONS_DIR / job.job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # metadata.json — URL at the top for quick access
    metadata = {
        "apply_url": job.url,
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "source": job.source,
        "salary": job.salary_range,
        "posted_date": job.posted_date,
        "prepared_at": datetime.now().isoformat(),
        "status": "prepared",
        "data_security": {
            "resume_sent_to_board": False,
            "contact_info_sent": False,
            "all_data_local": True,
        },
    }
    with open(job_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # jd.txt — full job description
    jd_content = f"""# {job.title} at {job.company}

**Location:** {job.location}
**Source:** {job.source}
**Posted:** {job.posted_date or 'Unknown'}
**Salary:** {job.salary_range or 'Not listed'}
**Apply:** {job.url}

---

{job.description if job.description else '[No description scraped — visit the apply URL for full JD]'}
"""
    with open(job_dir / "jd.txt", "w") as f:
        f.write(jd_content)

    # resume_tailored.md — rule-governed resume bullets
    resume_content = f"""# Tailored Resume — {job.title} at {job.company}

**RULES:** Based on general resume only. No fabrication. No embellishment.
**Source:** resume.txt + tailoring_rules.json

## Selected Experience Bullets

"""
    for i, bullet in enumerate(resume_bullets, 1):
        resume_content += f"{i}. {bullet}\n\n"

    resume_content += """## Certifications

GSEC | GCIH | GCIA | Security+ | CySA+ | PenTest+ | CASP+ | SecurityX | SSCP | CCNA | ITIL
AI/ML: CAISS | Ready Tensor: Agentic AI, LLM Engineering | ProtectAI: MLSecOps

## Education

- Postgraduate, AI & ML Engineering — University of Texas at Austin (McCombs) | 2025
- Applied Cybersecurity — SANS Technology Institute | 2024
- B.S., Cybersecurity & Information Assurance — Western Governors University | 2023
"""
    with open(job_dir / "resume_tailored.md", "w") as f:
        f.write(resume_content)

    # cover_letter.md
    with open(job_dir / "cover_letter.md", "w") as f:
        f.write(cover_letter)

    # screening_answers.json
    with open(job_dir / "screening_answers.json", "w") as f:
        json.dump(common_answers, f, indent=2)

    # review_checklist.md
    checklist_content = f"# Review Checklist — {job.title} at {job.company}\n\n"
    checklist_content += f"**Apply URL:** {job.url}\n\n"
    for item in review_checklist:
        checklist_content += f"- {item}\n"
    with open(job_dir / "review_checklist.md", "w") as f:
        f.write(checklist_content)

    # Update DB
    if db:
        db.set_materials_dir(job.job_id, str(job_dir))

    confirmation_code = hashlib.sha256(
        f"{job.job_id}:{metadata['prepared_at']}".encode()
    ).hexdigest()[:8].upper()

    audit_log("PREPARE_COMPLETED", job_id=job.job_id, materials_dir=str(job_dir))

    return {
        "job_id": job.job_id,
        "company": job.company,
        "title": job.title,
        "url": job.url,
        "materials_dir": str(job_dir),
        "confirmation_code": confirmation_code,
        "timestamp": metadata["prepared_at"],
    }


# ============================================================================
# SUBMIT WITH HUMAN GATE
# ============================================================================

def submit_manual(job_id: str, confirmation_code: str,
                  db: Optional[JobDatabase] = None) -> Dict:
    """Approve application for manual submission."""
    job_dir = APPLICATIONS_DIR / job_id
    meta_path = job_dir / "metadata.json"

    if not meta_path.exists():
        raise FileNotFoundError(f"No prepared materials found for {job_id}")

    with open(meta_path, "r") as f:
        metadata = json.load(f)

    expected = hashlib.sha256(
        f"{job_id}:{metadata['prepared_at']}".encode()
    ).hexdigest()[:8].upper()

    if confirmation_code.upper() != expected:
        audit_log("SUBMIT_FAILED", job_id=job_id, reason="invalid_code")
        raise PermissionError(f"Invalid confirmation code. Expected: {expected}")

    audit_log("SUBMIT_APPROVED", job_id=job_id, human_approved=True)

    if db:
        db.update_status(job_id, "approved", "human", "Human-approved via confirmation code")

    return {
        "job_id": job_id,
        "status": "approved",
        "next_step": f"Apply at: {metadata.get('apply_url', 'N/A')}",
        "materials": str(job_dir),
    }


# ============================================================================
# EMAIL NOTIFICATION
# ============================================================================

def send_email_digest(subject: str, body_html: str, body_text: str):
    """Send digest email via Gmail SMTP with TLS. Gracefully fails if not configured."""
    if not EMAIL_FROM or not EMAIL_PASSWORD:
        logger.info("Email not configured (CLAWGUARD_EMAIL_FROM/PASSWORD not set), skipping")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

        logger.info(f"Email digest sent to {EMAIL_TO}")
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        return False


def format_email_html(digest: Dict) -> Tuple[str, str]:
    """Format digest as HTML email and plain text."""
    s = digest["summary"]
    matches = digest.get("top_matches", [])

    # Plain text
    lines = [
        f"ClawGuard Job Digest — {digest['date']}",
        f"Found {s['total_found']} jobs, {s['new_jobs']} new",
        f"Strong: {s['strong_matches']} | Good: {s['good_matches']} | Moderate: {s['moderate_matches']}",
        f"Auto-prepared: {s.get('auto_prepared', 0)} jobs",
        f"Credits: {s['credits_remaining']} remaining",
        "",
    ]
    for i, m in enumerate(matches[:15], 1):
        lines.append(f"{i}. [{m['score']:.0%}] {m['title']} @ {m['company']}")
        lines.append(f"   {m['location']} | {m['source']} | {m.get('salary', 'N/A')}")
        if m.get("url"):
            lines.append(f"   Apply: {m['url']}")
        if m.get("materials_dir"):
            lines.append(f"   Materials: {m['materials_dir']}")
        lines.append("")
    text = "\n".join(lines)

    # HTML
    rows = ""
    for i, m in enumerate(matches[:15], 1):
        color = {"STRONG_MATCH": "#22c55e", "GOOD_MATCH": "#3b82f6",
                 "MODERATE_MATCH": "#eab308"}.get(m["recommendation"], "#9ca3af")
        link = f'<a href="{m["url"]}">Apply</a>' if m.get("url") else "N/A"
        prepared = "✅" if m.get("materials_dir") else ""
        rows += f"""<tr>
            <td>{i}</td>
            <td style="color:{color};font-weight:bold">{m['score']:.0%}</td>
            <td><strong>{m['title']}</strong><br><small>{m['company']}</small></td>
            <td>{m['location']}</td>
            <td>{m['source']}</td>
            <td>{m.get('salary', '')}</td>
            <td>{link}</td>
            <td>{prepared}</td>
        </tr>"""

    html = f"""<html><body style="font-family:sans-serif">
    <h2>ClawGuard Job Digest — {digest['date']}</h2>
    <p>Found <strong>{s['total_found']}</strong> jobs, <strong>{s['new_jobs']}</strong> new today.
    Auto-prepared materials for <strong>{s.get('auto_prepared', 0)}</strong> jobs.</p>
    <p>🟢 Strong: {s['strong_matches']} | 🔵 Good: {s['good_matches']} | 🟡 Moderate: {s['moderate_matches']}</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
    <tr style="background:#f3f4f6"><th>#</th><th>Score</th><th>Position</th><th>Location</th><th>Source</th><th>Salary</th><th>Apply</th><th>Prepared</th></tr>
    {rows}
    </table>
    <p style="margin-top:16px">Credits remaining: {s['credits_remaining']}</p>
    <p><small>Materials saved to: /data/clawguard/applications/</small></p>
    </body></html>"""

    return html, text


# ============================================================================
# DAILY DIGEST
# ============================================================================

def run_daily_digest(
    site: Optional[str] = None,
    compile_only: bool = False,
    sites: Optional[List[str]] = None,
    budget_limit: int = 50,
    min_score: float = MIN_SCORE_THRESHOLD,
    auto_prepare: bool = True,
    send_notification: bool = True,
    output_format: str = "json",
) -> Dict:
    """
    Run daily digest. Three modes:
    1. --site X: search single site, store to DB, exit (staggered cron)
    2. --compile: no searching, compile today's results from DB, notify
    3. (default): search all sites + compile (legacy mode)
    """
    db = JobDatabase()
    rate_limiter = RateLimiter(db)
    profile = load_profile()
    tailoring = TailoringEngine(profile.resume_text, TAILORING_RULES_PATH)

    locations = profile.target_locations
    primary_location = next(
        (loc for loc in locations if loc.lower() != "remote"),
        locations[0] if locations else "Seattle, WA"
    )

    new_jobs_total = 0

    if not compile_only:
        # Search mode
        search_sites = [site] if site else sites
        if search_sites is None:
            search_sites = [k for k, v in SITE_CONFIGS.items() if v.get("enabled")]

        for query_group in QUERY_GROUPS:
            remaining = db.get_remaining_credits()
            if remaining < 1:
                logger.info("No credits remaining, stopping")
                break
            effective_budget = min(budget_limit, remaining)

            _, new_count = search_all_sites(
                query=query_group, location=primary_location,
                sites=search_sites, max_results_per_site=10,
                budget_limit=effective_budget, db=db, rate_limiter=rate_limiter,
            )
            new_jobs_total += new_count

        if site:
            # Single-site mode: just report and exit
            logger.info(f"Single-site digest ({site}): {new_jobs_total} new jobs added to DB")
            return {"site": site, "new_jobs": new_jobs_total, "mode": "single-site"}

    # ── Compile mode: score, auto-prepare, build digest ──

    # Step 1: Quick-score all unscored jobs (uses existing thin descriptions)
    # This gives us title_match data for enrichment prioritization
    today_jobs_data = db.get_digest_jobs()
    first_week = db.is_first_week()
    mode_label = "first-week (all jobs)" if first_week else "daily (last 24h)"
    logger.info(f"Compiling digest ({mode_label}): {len(today_jobs_data)} jobs")

    # Convert DB rows to Job objects for scoring
    all_jobs = []
    for row in today_jobs_data:
        all_jobs.append(Job(
            job_id=row["job_id"], title=row["title"], company=row["company"],
            location=row["location"] or "", description=row["description"] or "",
            url=row["url"] or "", source=row["source"] or "",
            posted_date=row["posted_date"], salary_range=row["salary_range"],
        ))

    # Score unscored jobs
    scored = []
    for job in all_jobs:
        existing = db.get_job(job.job_id)
        if existing and existing.get("score") is not None:
            # Already scored, reconstruct ScoredJob
            scored.append(ScoredJob(
                job=job, score=existing["score"],
                matched_skills=json.loads(existing["matched_skills"] or "[]"),
                missing_skills=json.loads(existing["missing_skills"] or "[]"),
                matched_certs=json.loads(existing["matched_certs"] or "[]"),
                title_match=bool(existing["title_match"]),
                recommendation=existing["recommendation"] or "WEAK_MATCH",
            ))
        else:
            scored.append(score_job(job, profile, db=db))

    scored.sort(key=lambda s: s.score, reverse=True)

    # Step 2: Enrich top jobs with full JDs (budget-capped, title-match prioritized)
    # This runs AFTER initial scoring so we know which jobs deserve enrichment
    enrichment_count = enrich_top_jobs(db, rate_limiter, daily_cap=ENRICHMENT_DAILY_CAP)

    # Step 3: Re-score enriched jobs (now with full JD data for better skill matching)
    if enrichment_count > 0:
        logger.info(f"Re-scoring {enrichment_count} enriched jobs")
        rescored = []
        for s in scored:
            # Re-read from DB to get enriched description
            fresh = db.get_job(s.job.job_id)
            if fresh and fresh.get("description") and len(fresh["description"]) > len(s.job.description):
                # Job was enriched — re-score with full JD
                enriched_job = Job(
                    job_id=s.job.job_id, title=s.job.title, company=s.job.company,
                    location=s.job.location, description=fresh["description"],
                    url=fresh.get("url") or s.job.url, source=s.job.source,
                    posted_date=s.job.posted_date, salary_range=s.job.salary_range,
                )
                rescored.append(score_job(enriched_job, profile, db=db))
            else:
                rescored.append(s)
        scored = rescored
        scored.sort(key=lambda s: s.score, reverse=True)

    # Auto-prepare STRONG + GOOD matches
    auto_prepared = 0
    if auto_prepare:
        for s in scored:
            if s.score >= AUTO_PREPARE_THRESHOLD:
                existing = db.get_job(s.job.job_id)
                if existing and existing.get("materials_dir"):
                    continue  # Already prepared
                try:
                    prepare_application(s.job, profile, tailoring, db)
                    auto_prepared += 1
                    logger.info(f"Auto-prepared: {s.job.title} @ {s.job.company} ({s.score:.0%})")
                except Exception as e:
                    logger.warning(f"Auto-prepare failed for {s.job.job_id}: {e}")

    # Build digest
    strong = [s for s in scored if s.recommendation == "STRONG_MATCH"]
    good = [s for s in scored if s.recommendation == "GOOD_MATCH"]
    moderate = [s for s in scored if s.recommendation == "MODERATE_MATCH"]

    used, total = db.get_quota()

    digest = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_found": len(all_jobs),
            "new_jobs": new_jobs_total if not compile_only else len(all_jobs),
            "strong_matches": len(strong),
            "good_matches": len(good),
            "moderate_matches": len(moderate),
            "auto_prepared": auto_prepared,
            "credits_used_today": used,
            "credits_remaining": total - used,
            "total_jobs_in_db": db.get_total_count(),
        },
        "top_matches": [
            {
                "job_id": s.job.job_id,
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
                "materials_dir": str(APPLICATIONS_DIR / s.job.job_id)
                    if s.score >= AUTO_PREPARE_THRESHOLD else None,
            }
            for s in scored if s.score >= min_score
        ][:25],
        "query_groups_used": QUERY_GROUPS,
        "sites_searched": sites or [site] if site else list(SITE_CONFIGS.keys()),
        "location": primary_location,
    }

    # Save digest
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIGESTS_DIR / f"digest_{digest['date']}.json"
    with open(archive_path, "w") as f:
        json.dump(digest, f, indent=2)

    # Send notifications
    if send_notification and compile_only or (not site and send_notification):
        # Email
        html, text = format_email_html(digest)
        subject = (
            f"ClawGuard: {len(strong)} strong + {len(good)} good matches "
            f"({len(all_jobs)} total) — {digest['date']}"
        )
        send_email_digest(subject, html, text)

    db.close()
    return digest


def format_digest_telegram(digest: Dict) -> str:
    s = digest["summary"]
    lines = [
        f"\U0001f4cb **Job Search Digest — {digest['date']}**",
        f"",
        f"\U0001f50d Found **{s['total_found']}** jobs | **{s.get('new_jobs', '?')}** new today",
        f"\U0001f7e2 Strong: **{s['strong_matches']}** | \U0001f535 Good: **{s['good_matches']}** | "
        f"\U0001f7e1 Moderate: **{s['moderate_matches']}**",
        f"\U00002705 Auto-prepared: **{s.get('auto_prepared', 0)}** application packages",
        f"\U0001f4b0 Credits: {s['credits_remaining']} remaining | DB: {s.get('total_jobs_in_db', '?')} total jobs",
        f"",
    ]

    for i, match in enumerate(digest["top_matches"][:15], 1):
        emoji = {
            "STRONG_MATCH": "\U0001f7e2", "GOOD_MATCH": "\U0001f535",
            "MODERATE_MATCH": "\U0001f7e1"
        }.get(match["recommendation"], "\u26aa")
        title_flag = " \U0001f3af" if match["title_match"] else ""
        salary = f" | {match['salary']}" if match.get("salary") else ""
        prepared = " \U0001f4e6" if match.get("materials_dir") else ""
        lines.append(
            f"{emoji} **{i}. {match['title']}** @ {match['company']}{title_flag}{prepared}"
        )
        lines.append(
            f"   \U0001f4cd {match['location']} | {match['source'].capitalize()}{salary}"
        )
        lines.append(
            f"   Score: {match['score']:.0%} | Skills: {', '.join(match['matched_skills'][:3])}"
        )
        if match.get("url"):
            lines.append(f"   \U0001f517 {match['url']}")
        lines.append("")

    lines.append("\U0001f4e6 = materials auto-prepared in /data/clawguard/applications/")
    lines.append("Use `prepare --job-id <ID>` for additional jobs.")
    return "\n".join(lines)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ClawGuard Job Search Pipeline v2"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ── init-db ──
    subparsers.add_parser("init-db", help="Initialize the SQLite database")

    # ── search ──
    sp = subparsers.add_parser("search", help="Search for jobs")
    sp.add_argument("--query", required=True)
    sp.add_argument("--location", "--locations", dest="locations", required=True)
    sp.add_argument("--max-results", type=int, default=10)
    sp.add_argument("--output", help="Also save to JSON file")
    sp.add_argument("--sites", help="Comma-separated site keys or 'all'")
    sp.add_argument("--budget", type=int, help="Max credits")
    sp.add_argument("--since", help="Only show jobs posted since (e.g. '24h', '7d')")

    # ── score ──
    sp = subparsers.add_parser("score", help="Score jobs against resume")
    sp.add_argument("--jobs", help="JSON file with jobs (legacy)")
    sp.add_argument("--status", default="found", help="Score jobs with this status from DB")
    sp.add_argument("--profile")
    sp.add_argument("--min-score", type=float, default=MIN_SCORE_THRESHOLD)
    sp.add_argument("--output")

    # ── prepare ──
    sp = subparsers.add_parser("prepare", help="Prepare application materials")
    sp.add_argument("--job-id", required=True)
    sp.add_argument("--job-file", help="JSON file with job details (legacy)")
    sp.add_argument("--profile")
    sp.add_argument("--output", help="Legacy: output JSON file")

    # ── submit ──
    sp = subparsers.add_parser("submit", help="Approve application (human gate)")
    sp.add_argument("--job-id", required=True)
    sp.add_argument("--confirmation-code", required=True)

    # ── digest ──
    sp = subparsers.add_parser("digest", help="Daily digest")
    sp.add_argument("--site", help="Single site key (staggered mode)")
    sp.add_argument("--compile", action="store_true", help="Compile only, no new searches")
    sp.add_argument("--budget", type=int, default=50)
    sp.add_argument("--min-score", type=float, default=MIN_SCORE_THRESHOLD)
    sp.add_argument("--sites", help="Comma-separated site keys")
    sp.add_argument("--format", choices=["json", "telegram"], default="json")
    sp.add_argument("--no-prepare", action="store_true", help="Skip auto-prepare")
    sp.add_argument("--no-notify", action="store_true", help="Skip notifications")

    # ── track ──
    sp = subparsers.add_parser("track", help="Update job status")
    sp.add_argument("--job-id", required=True)
    sp.add_argument("--status", required=True,
                    choices=["found", "scored", "prepared", "reviewed",
                             "applied", "interview", "offer", "rejected"])
    sp.add_argument("--notes", default="")

    # ── browse ──
    sp = subparsers.add_parser("browse", help="Browse jobs in database")
    sp.add_argument("--status", help="Filter by status")
    sp.add_argument("--since", help="Jobs found since (e.g. '24h', '7d')")
    sp.add_argument("--job-id", help="Show single job details")
    sp.add_argument("--summary", action="store_true", help="Pipeline summary")
    sp.add_argument("--limit", type=int, default=25)

    # ── export ──
    sp = subparsers.add_parser("export", help="Export job data")
    sp.add_argument("--status", help="Filter by status")
    sp.add_argument("--job-id", help="Export single job")
    sp.add_argument("--format", choices=["json", "csv"], default="json")
    sp.add_argument("--output", required=True)

    # ── quota ──
    subparsers.add_parser("quota", help="Credit quota status")

    # ── sites ──
    subparsers.add_parser("sites", help="List available job sites")

    # ── migrate ──
    sp = subparsers.add_parser("migrate", help="Migrate old JSON data to SQLite")
    sp.add_argument("--source", help="Directory with old digest JSON files")

    args = parser.parse_args()
    setup_logging()

    if not args.command:
        parser.print_help()
        return

    # ══════════════════════════════════════════════
    # init-db
    # ══════════════════════════════════════════════
    if args.command == "init-db":
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
        db = JobDatabase()
        db.close()
        # Copy default tailoring rules if not present
        if not TAILORING_RULES_PATH.exists():
            with open(TAILORING_RULES_PATH, "w") as f:
                json.dump(TailoringEngine.DEFAULT_RULES, f, indent=2)
            logger.info(f"Created default tailoring rules: {TAILORING_RULES_PATH}")
        print(f"Database initialized: {DB_PATH}")
        print(f"Applications dir: {APPLICATIONS_DIR}")
        print(f"Tailoring rules: {TAILORING_RULES_PATH}")

    # ══════════════════════════════════════════════
    # search
    # ══════════════════════════════════════════════
    elif args.command == "search":
        db = JobDatabase()
        rl = RateLimiter(db)
        locations = [l.strip() for l in args.locations.split(",")]
        location_str = locations[0]

        if args.sites:
            site_keys = None if args.sites.lower() == "all" else [s.strip() for s in args.sites.split(",")]
        else:
            site_keys = ["linkedin"]

        if site_keys and len(site_keys) == 1:
            jobs, new_count = search_site(
                site_keys[0], args.query, location_str, args.max_results,
                db=db, rate_limiter=rl,
            )
        else:
            jobs, new_count = search_all_sites(
                args.query, location_str, sites=site_keys,
                max_results_per_site=args.max_results,
                budget_limit=args.budget, db=db, rate_limiter=rl,
            )

        if args.output:
            with open(args.output, "w") as f:
                json.dump([asdict(j) for j in jobs], f, indent=2)

        for job in jobs:
            existing = db.get_job(job.job_id)
            new_flag = " [NEW]" if existing and existing["first_seen"] == existing["last_seen"] else ""
            print(f"[{job.source}]{new_flag} {job.title} at {job.company} ({job.location})")
            if job.url:
                print(f"  → {job.url}")

        print(f"\nTotal: {len(jobs)} jobs found, {new_count} new (not previously seen)")
        db.close()

    # ══════════════════════════════════════════════
    # score
    # ══════════════════════════════════════════════
    elif args.command == "score":
        db = JobDatabase()
        profile = load_profile(args.profile)

        if args.jobs:
            # Legacy: load from JSON file
            with open(args.jobs, "r") as f:
                jobs_data = json.load(f)
            jobs = [Job(**j) for j in jobs_data]
        else:
            # Default: score from DB
            rows = db.get_jobs_by_status(args.status)
            jobs = [Job(
                job_id=r["job_id"], title=r["title"], company=r["company"],
                location=r["location"] or "", description=r["description"] or "",
                url=r["url"] or "", source=r["source"] or "",
                posted_date=r["posted_date"], salary_range=r["salary_range"],
            ) for r in rows]

        scored = [score_job(job, profile, db=db) for job in jobs]
        scored.sort(key=lambda s: s.score, reverse=True)
        filtered = [s for s in scored if s.score >= args.min_score]

        for s in filtered:
            emoji = {"STRONG_MATCH": "\U0001f7e2", "GOOD_MATCH": "\U0001f535",
                     "MODERATE_MATCH": "\U0001f7e1", "WEAK_MATCH": "\u26aa"}[s.recommendation]
            print(f"{emoji} [{s.score:.0%}] {s.job.title} at {s.job.company}")
            print(f"  Skills: {', '.join(s.matched_skills[:5])}")
            if s.missing_skills:
                print(f"  Missing: {', '.join(s.missing_skills[:3])}")
            if s.matched_certs:
                print(f"  Certs: {', '.join(s.matched_certs)}")
            print(f"  Title match: {'Yes \U0001f3af' if s.title_match else 'No'}")
            print()

        print(f"Showing {len(filtered)}/{len(scored)} jobs above {args.min_score:.0%}")

        if args.output:
            out = [{**asdict(s.job), "score": s.score, "recommendation": s.recommendation,
                    "matched_skills": s.matched_skills, "missing_skills": s.missing_skills}
                   for s in filtered]
            with open(args.output, "w") as f:
                json.dump(out, f, indent=2)
        db.close()

    # ══════════════════════════════════════════════
    # prepare
    # ══════════════════════════════════════════════
    elif args.command == "prepare":
        db = JobDatabase()
        profile = load_profile(args.profile)
        tailoring = TailoringEngine(profile.resume_text, TAILORING_RULES_PATH)

        # Try DB first, fall back to file
        job_data = db.get_job(args.job_id)
        if job_data:
            job = Job(
                job_id=job_data["job_id"], title=job_data["title"],
                company=job_data["company"], location=job_data["location"] or "",
                description=job_data["description"] or "", url=job_data["url"] or "",
                source=job_data["source"] or "",
                posted_date=job_data["posted_date"], salary_range=job_data["salary_range"],
            )
        elif args.job_file:
            with open(args.job_file, "r") as f:
                jobs_data = json.load(f)
            job = None
            for j in jobs_data:
                if j.get("job_id") == args.job_id:
                    job = Job(**j)
                    break
            if not job:
                print(f"Job ID '{args.job_id}' not found")
                sys.exit(1)
        else:
            print(f"Job ID '{args.job_id}' not found in database. Use --job-file for legacy mode.")
            sys.exit(1)

        result = prepare_application(job, profile, tailoring, db)
        print(f"\n\u2705 Materials prepared: {result['title']} at {result['company']}")
        print(f"\U0001f4c1 Directory: {result['materials_dir']}")
        print(f"\U0001f517 Apply URL: {result['url']}")
        print(f"\U0001f511 Confirmation code: {result['confirmation_code']}")
        print(f"\u26a0\ufe0f  Review all [HUMAN:] sections before submitting!")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
        db.close()

    # ══════════════════════════════════════════════
    # submit
    # ══════════════════════════════════════════════
    elif args.command == "submit":
        db = JobDatabase()
        result = submit_manual(args.job_id, args.confirmation_code, db)
        print(f"\n\u2705 Application approved: {args.job_id}")
        print(f"\U0001f517 {result['next_step']}")
        print(f"\U0001f4c1 Materials: {result['materials']}")
        db.close()

    # ══════════════════════════════════════════════
    # digest
    # ══════════════════════════════════════════════
    elif args.command == "digest":
        sites_list = [s.strip() for s in args.sites.split(",")] if args.sites else None
        digest = run_daily_digest(
            site=args.site,
            compile_only=args.compile,
            sites=sites_list,
            budget_limit=args.budget,
            min_score=args.min_score,
            auto_prepare=not args.no_prepare,
            send_notification=not args.no_notify,
            output_format=args.format,
        )

        if args.format == "telegram":
            print(format_digest_telegram(digest))
        else:
            print(json.dumps(digest, indent=2))

    # ══════════════════════════════════════════════
    # track
    # ══════════════════════════════════════════════
    elif args.command == "track":
        db = JobDatabase()
        db.update_status(args.job_id, args.status, "human", args.notes)
        print(f"Updated {args.job_id} → {args.status}")
        db.close()

    # ══════════════════════════════════════════════
    # browse
    # ══════════════════════════════════════════════
    elif args.command == "browse":
        db = JobDatabase()

        if args.summary:
            counts = db.get_job_count()
            total = db.get_total_count()
            used, quota_total = db.get_quota()
            print(f"\U0001f4ca ClawGuard Pipeline Summary")
            print(f"{'─' * 40}")
            print(f"Total jobs in DB: {total}")
            for status, cnt in sorted(counts.items()):
                print(f"  {status}: {cnt}")
            print(f"Credits: {used}/{quota_total} used, {quota_total - used} remaining")
            db.close()
            return

        if args.job_id:
            job = db.get_job(args.job_id)
            if not job:
                print(f"Job {args.job_id} not found")
            else:
                print(f"\U0001f4cb Job Details: {job['job_id']}")
                print(f"{'─' * 50}")
                print(f"Title:    {job['title']}")
                print(f"Company:  {job['company']}")
                print(f"Location: {job['location']}")
                print(f"Source:   {job['source']}")
                print(f"URL:      {job['url']}")
                print(f"Score:    {job['score']:.0%}" if job['score'] else "Score:    Not scored")
                print(f"Status:   {job['status']}")
                print(f"First seen: {job['first_seen']}")
                print(f"Salary:   {job['salary_range'] or 'N/A'}")
                if job['materials_dir']:
                    print(f"Materials: {job['materials_dir']}")
                if job['matched_skills']:
                    skills = json.loads(job['matched_skills'])
                    print(f"Skills:   {', '.join(skills)}")
            db.close()
            return

        # List jobs
        if args.since:
            unit = args.since[-1]
            num = int(args.since[:-1])
            if unit == 'h':
                since = (datetime.now() - timedelta(hours=num)).isoformat()
            elif unit == 'd':
                since = (datetime.now() - timedelta(days=num)).isoformat()
            else:
                since = args.since
            rows = db.get_new_jobs_since(since)[:args.limit]
        elif args.status:
            rows = db.get_jobs_by_status(args.status, args.limit)
        else:
            rows = db.get_todays_new_jobs()[:args.limit]

        for r in rows:
            score_str = f"{r['score']:.0%}" if r['score'] else "---"
            prepared = " \U0001f4e6" if r['materials_dir'] else ""
            print(f"[{score_str}] {r['title']} @ {r['company']} ({r['source']}){prepared}")
            print(f"  Status: {r['status']} | ID: {r['job_id']}")

        print(f"\n{len(rows)} jobs shown")
        db.close()

    # ══════════════════════════════════════════════
    # export
    # ══════════════════════════════════════════════
    elif args.command == "export":
        db = JobDatabase()

        if args.job_id:
            rows = [db.get_job(args.job_id)]
            rows = [r for r in rows if r]
        elif args.status:
            rows = db.get_jobs_by_status(args.status, 1000)
        else:
            rows = db.get_new_jobs_since("2000-01-01")

        if args.format == "csv":
            import csv
            with open(args.output, "w", newline="") as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
        else:
            with open(args.output, "w") as f:
                json.dump(rows, f, indent=2, default=str)

        print(f"Exported {len(rows)} jobs to {args.output}")
        db.close()

    # ══════════════════════════════════════════════
    # quota
    # ══════════════════════════════════════════════
    elif args.command == "quota":
        db = JobDatabase()
        used, total = db.get_quota()
        print(f"Oxylabs Credit Quota:")
        print(f"  Used:      {used}")
        print(f"  Total:     {total}")
        print(f"  Remaining: {total - used}")
        print(f"  Month:     {datetime.now().strftime('%Y-%m')}")
        db.close()

    # ══════════════════════════════════════════════
    # sites
    # ══════════════════════════════════════════════
    elif args.command == "sites":
        print("Available Job Sites:")
        print(f"{'Key':<15} {'Name':<20} {'JS?':<5} {'Credits':<8} {'Status'}")
        print("-" * 60)
        for key, config in SITE_CONFIGS.items():
            status = "\u2705 Enabled" if config.get("enabled") else "\u274c Disabled"
            js = "Yes" if config["needs_js"] else "No"
            print(f"{key:<15} {config['name']:<20} {js:<5} {config['credits_per_page']:<8} {status}")

    # ══════════════════════════════════════════════
    # migrate
    # ══════════════════════════════════════════════
    elif args.command == "migrate":
        db = JobDatabase()
        source_dir = Path(args.source) if args.source else SKILL_DIR / "digests"
        migrated = 0

        if source_dir.exists():
            for digest_file in sorted(source_dir.glob("digest_*.json")):
                try:
                    with open(digest_file, "r") as f:
                        digest = json.load(f)
                    for match in digest.get("top_matches", []):
                        job = Job(
                            job_id=match.get("job_id", hashlib.md5(
                                f"{match['title']}{match['company']}".encode()
                            ).hexdigest()[:12]),
                            title=match["title"], company=match["company"],
                            location=match.get("location", ""),
                            description="", url=match.get("url", ""),
                            source=match.get("source", "unknown"),
                            posted_date=match.get("posted"),
                            salary_range=match.get("salary"),
                        )
                        if db.upsert_job(job):
                            migrated += 1
                except Exception as e:
                    logger.warning(f"Migration error for {digest_file}: {e}")

        print(f"Migrated {migrated} jobs from {source_dir}")
        db.close()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
