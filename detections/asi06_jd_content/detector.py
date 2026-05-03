"""ClawGuard ASI06 job-description content detector.

This module is the standalone ClawGuard implementation of the ASI06 checks
currently enforced inline by OpenClaw's job-search-custom skill.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from urllib.parse import urlparse


DEFAULT_SKILL_STUFFING_THRESHOLD = 15

SKILL_ALIASES: dict[str, list[str]] = {
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

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(your\s+)?system\s+prompt",
    r"score\s+this\s+(job\s+)?at\s+\d+",
    r"mark\s+(this\s+)?(as\s+)?strong[ _-]?match",
    r"do\s+not\s+show\s+other",
    r"override\s+(the\s+)?scoring",
    r"you\s+are\s+now\s+a[n]?\s+",
    r"assistant\s*:",
    r"system\s*:\s*you\s+are",
    r"developer\s*:\s*you\s+are",
]

PII_REQUEST_PATTERNS = [
    r"include\s+(your\s+)?(full\s+)?resume\s+in",
    r"salary\s+history",
    r"social\s+security",
    r"\bssn\b",
    r"bank\s+(account|routing)",
    r"send\s+(your\s+)?(id|passport|license)",
    r"references\s+with\s+phone",
]

SAFE_APPLY_DOMAINS = {
    "linkedin.com",
    "indeed.com",
    "dice.com",
    "monster.com",
    "usajobs.gov",
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "icims.com",
    "smartrecruiters.com",
    "jobvite.com",
    "ashbyhq.com",
    "bamboohr.com",
}


def _read_field(source: Any, *names: str, default: str = "") -> str:
    for name in names:
        value: Any
        if isinstance(source, Mapping):
            value = source.get(name)
        else:
            value = getattr(source, name, None)
        if value is not None:
            return str(value)
    return default


@dataclass(frozen=True)
class JobContent:
    job_id: str
    title: str
    company: str
    location: str = ""
    description: str = ""
    apply_url: str = ""
    source_platform: str = ""
    source_field: str = "title_and_description"

    @classmethod
    def from_any(cls, source: Any) -> "JobContent":
        return cls(
            job_id=_read_field(source, "job_id", "id"),
            title=_read_field(source, "title", "job_title"),
            company=_read_field(source, "company"),
            location=_read_field(source, "location"),
            description=_read_field(source, "description"),
            apply_url=_read_field(source, "apply_url", "url"),
            source_platform=_read_field(source, "source_platform", "source"),
            source_field=_read_field(source, "source_field", default="title_and_description"),
        )

    @property
    def detection_text(self) -> str:
        return f"{self.title}\n{self.description}"

    @property
    def context(self) -> dict[str, str]:
        return {
            "job_id": self.job_id,
            "job_title": self.title,
            "company": self.company,
            "source_platform": self.source_platform,
            "apply_url": self.apply_url,
            "source_field": self.source_field,
        }


@dataclass(frozen=True)
class DetectionFinding:
    rule_id: str
    severity: str
    message: str
    evidence: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)

    def to_record(self, agent_session_id: Optional[str] = None) -> dict[str, Any]:
        return {
            "job_id": self.context.get("job_id", ""),
            "agent_session_id": agent_session_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": json.dumps(self.evidence, sort_keys=True),
            "context": json.dumps(self.context, sort_keys=True),
        }


def extract_skills(text: str, skill_aliases: Optional[Mapping[str, list[str]]] = None) -> list[str]:
    aliases_by_skill = skill_aliases or SKILL_ALIASES
    text_lower = text.lower()
    found = []
    for canonical, aliases in aliases_by_skill.items():
        if any(alias in text_lower for alias in aliases):
            found.append(canonical)
    return found


def _domain_matches_company(company: str, domain: str) -> bool:
    company_slug = re.sub(r"[^a-z0-9]", "", company.lower())
    domain_slug = re.sub(r"[^a-z0-9]", "", domain.lower())
    if not company_slug or company_slug in {"unknowncompany", "unknownagency"}:
        return True
    return company_slug in domain_slug or domain_slug in company_slug


def _pattern_evidence(patterns: list[str], text: str) -> list[dict[str, str]]:
    matches = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        start = max(match.start() - 60, 0)
        end = min(match.end() + 60, len(text))
        matches.append({
            "pattern": pattern,
            "matched_text": match.group(0),
            "snippet": re.sub(r"\s+", " ", text[start:end]).strip(),
        })
    return matches


class ASI06JobContentDetector:
    def __init__(
        self,
        skill_stuffing_threshold: int = DEFAULT_SKILL_STUFFING_THRESHOLD,
        skill_aliases: Optional[Mapping[str, list[str]]] = None,
        safe_apply_domains: Optional[set[str]] = None,
    ):
        self.skill_stuffing_threshold = skill_stuffing_threshold
        self.skill_aliases = skill_aliases or SKILL_ALIASES
        self.safe_apply_domains = safe_apply_domains or SAFE_APPLY_DOMAINS

    def detect(self, job: Any, jd_text: Optional[str] = None) -> list[DetectionFinding]:
        content = JobContent.from_any(job)
        text = jd_text if jd_text is not None else content.detection_text
        findings = [
            self.detect_skill_stuffing(text),
            self.detect_apply_url_mismatch(content.company, content.apply_url),
            self.detect_prompt_injection(text),
            self.detect_pii_request(text),
        ]
        return [
            DetectionFinding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                message=finding.message,
                evidence=finding.evidence,
                context={**content.context, **finding.context},
            )
            for finding in findings
            if finding is not None
        ]

    def detect_skill_stuffing(self, jd_text: str) -> Optional[DetectionFinding]:
        skills_found = extract_skills(jd_text, self.skill_aliases)
        if len(skills_found) <= self.skill_stuffing_threshold:
            return None
        return DetectionFinding(
            rule_id="ASI06_SKILL_STUFFING",
            severity="MEDIUM",
            message=(
                f"Job description contains {len(skills_found)} canonical skill matches; "
                f"threshold is {self.skill_stuffing_threshold}."
            ),
            evidence={
                "skill_count": len(skills_found),
                "threshold": self.skill_stuffing_threshold,
                "skills": skills_found,
            },
        )

    def detect_apply_url_mismatch(self, company: str, apply_url: str) -> Optional[DetectionFinding]:
        if not apply_url:
            return None
        domain = urlparse(apply_url).netloc.lower()
        domain = domain[4:] if domain.startswith("www.") else domain
        if not domain:
            return None
        if any(domain == safe or domain.endswith(f".{safe}") for safe in self.safe_apply_domains):
            return None
        if _domain_matches_company(company, domain):
            return None
        return DetectionFinding(
            rule_id="ASI06_URL_MISMATCH",
            severity="MEDIUM",
            message=f"Apply URL domain '{domain}' does not match company '{company}'.",
            evidence={"company": company, "domain": domain, "url": apply_url},
        )

    def detect_prompt_injection(self, jd_text: str) -> Optional[DetectionFinding]:
        matches = _pattern_evidence(INJECTION_PATTERNS, jd_text)
        if not matches:
            return None
        return DetectionFinding(
            rule_id="ASI06_PROMPT_INJECTION",
            severity="HIGH",
            message="Job description contains prompt-injection language.",
            evidence={"matches": matches},
        )

    def detect_pii_request(self, jd_text: str) -> Optional[DetectionFinding]:
        matches = _pattern_evidence(PII_REQUEST_PATTERNS, jd_text)
        if not matches:
            return None
        return DetectionFinding(
            rule_id="ASI06_PII_REQUEST",
            severity="HIGH",
            message="Job description requests sensitive personal data outside normal application flow.",
            evidence={"matches": matches},
        )


def detect_job_content(job: Any, jd_text: Optional[str] = None) -> list[DetectionFinding]:
    return ASI06JobContentDetector().detect(job, jd_text=jd_text)
