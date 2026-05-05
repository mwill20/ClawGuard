"""ClawGuard ASI02 tool-misuse detector.

ASI02 v1 is content-side and pre-action. It detects untrusted job content that
instructs OpenClaw to misuse tools such as HTTP egress, notifications, shell,
or file writes. Runtime tool-call instrumentation is a later phase.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import urlparse

from ..asi06_jd_content.detector import (
    DetectionFinding,
    JobContent,
)


SAFE_EGRESS_DOMAINS = {
    "api.search.brave.com",
    "data.usajobs.gov",
    "linkedin.com",
    "usajobs.gov",
    "cybersecjobs.com",
}

DEFAULT_SAFE_DATA_ROOT = "/data/clawguard"

URL_RE = r"https?://[^\s`'\"<>)]+"
EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_RE = r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}"

EGRESS_PATTERNS = [
    rf"\b(?:run|execute|invoke|use)\s+(?:curl|wget)\s+(?P<url>{URL_RE})",
    rf"\b(?:curl|wget)\s+(?P<url>{URL_RE})",
    rf"\b(?:fetch|post|upload|beacon|send)\b.{{0,80}}\b(?:to|at)\s+(?P<url>{URL_RE})",
]

NOTIFY_PATTERNS = [
    rf"\b(?:email|send|forward)\b.{{0,100}}\b(?:digest|results|summary|resume|profile|user\s+data)\b.{{0,80}}\b(?:to|at)\s+(?P<dest>{EMAIL_RE}|{PHONE_RE}|{URL_RE})",
    rf"\b(?:post|send|forward)\b.{{0,80}}\b(?:digest|results|summary|resume|profile|user\s+data)\b.{{0,120}}\b(?:webhook|slack|telegram|discord)\b.{{0,80}}(?P<dest>{URL_RE})",
]

SHELL_SNIPPET_PATTERNS = [
    r"(?:;|&&|\|\||`|\$\(|\|)\s*(?:curl|wget|bash|sh|python|powershell|nc|cat|rm|chmod|env|printenv|type)\b[^\n]*",
    r"\b(?:bash|sh|powershell|cmd|python)\s+-c\s+[`'\"][^`'\"]+[`'\"]",
    r"\b(?:rm\s+-rf|chmod\s+777|cat\s+/etc/passwd|type\s+\.env)\b[^\n]*",
]

SHELL_IMPERATIVE_RE = re.compile(
    r"\b(?:run|execute|invoke|pipe|append|eval|launch|spawn|open\s+a\s+shell)\b",
    re.IGNORECASE,
)
SHELL_DANGEROUS_SINK_RE = re.compile(
    r"(/etc/passwd|\.env\b|curl\b|wget\b|nc\b|rm\s+-rf|chmod\s+777|powershell\s+-enc)",
    re.IGNORECASE,
)

FILE_PATH_PATTERNS = [
    r"\b(?:write|save|store|copy|export)\b.{0,80}\b(?:to|under|at|into)\s+(?P<path>(?:\.\./|/|[A-Za-z]:\\)[^\s`'\"]+)",
]


def _coerce_findings(findings: Optional[Iterable[Any]]) -> tuple:
    if not findings:
        return ()
    return tuple(findings)


def _related_rule(findings: Iterable[Any], prefix: str) -> Optional[str]:
    for finding in findings:
        rule_id = getattr(finding, "rule_id", None)
        if rule_id is None and isinstance(finding, Mapping):
            rule_id = finding.get("rule_id")
        if isinstance(rule_id, str) and rule_id.startswith(prefix):
            return rule_id
    return None


def _snippet(text: str, start: int, end: int) -> str:
    left = max(start - 60, 0)
    right = min(end + 60, len(text))
    return re.sub(r"\s+", " ", text[left:right]).strip()


def _match_evidence(pattern: str, match: re.Match[str], text: str) -> dict[str, str]:
    return {
        "pattern": pattern,
        "matched_text": match.group(0),
        "snippet": _snippet(text, match.start(), match.end()),
    }


def _domain_allowed(url: str, safe_domains: set[str]) -> bool:
    domain = urlparse(url).netloc.lower()
    domain = domain[4:] if domain.startswith("www.") else domain
    if not domain:
        return False
    return any(domain == safe or domain.endswith(f".{safe}") for safe in safe_domains)


def _path_inside_root(path: str, safe_root: str) -> bool:
    normalized = path.replace("\\", "/")
    root = safe_root.rstrip("/")
    return normalized == root or normalized.startswith(f"{root}/")


class ASI02ToolMisuseDetector:
    """Detect content that attempts to drive unsafe tool use."""

    def __init__(
        self,
        safe_egress_domains: Optional[set[str]] = None,
        safe_data_root: str = DEFAULT_SAFE_DATA_ROOT,
    ):
        self.safe_egress_domains = safe_egress_domains or SAFE_EGRESS_DOMAINS
        self.safe_data_root = safe_data_root

    def detect(
        self,
        job: Any,
        jd_text: Optional[str] = None,
        asi06_findings: Optional[Iterable[Any]] = None,
        asi01_findings: Optional[Iterable[Any]] = None,
    ) -> list[DetectionFinding]:
        content = JobContent.from_any(job)
        text = jd_text if jd_text is not None else content.detection_text
        upstream_asi06 = _coerce_findings(asi06_findings)
        upstream_asi01 = _coerce_findings(asi01_findings)
        links = self._corroboration_links(upstream_asi06, upstream_asi01)

        findings = [
            self.detect_egress_redirect(text, content.context, links),
            self.detect_notify_redirect(text, content.context, links),
            self.detect_shell_injection(text, content.context, links),
            self.detect_file_path_redirect(text, content.context, links),
        ]
        return [finding for finding in findings if finding is not None]

    def _corroboration_links(
        self,
        asi06_findings: Iterable[Any],
        asi01_findings: Iterable[Any],
    ) -> dict[str, str]:
        links: dict[str, str] = {}
        asi06_rule = _related_rule(asi06_findings, "ASI06_")
        asi01_rule = _related_rule(asi01_findings, "ASI01_")
        if asi06_rule:
            links["related_asi06_rule_id"] = asi06_rule
        if asi01_rule:
            links["related_asi01_rule_id"] = asi01_rule
        return links

    def detect_egress_redirect(
        self,
        text: str,
        context: dict[str, Any],
        links: dict[str, str],
    ) -> Optional[DetectionFinding]:
        for pattern in EGRESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            url = match.group("url")
            if _domain_allowed(url, self.safe_egress_domains):
                continue
            domain = urlparse(url).netloc.lower()
            evidence = {
                "attempted_operation_category": "http-egress",
                "destination_url": url,
                "destination_domain": domain,
                "matches": [_match_evidence(pattern, match, text)],
                **links,
            }
            return DetectionFinding(
                rule_id="ASI02_EGRESS_REDIRECT",
                severity="HIGH",
                message="External content instructs the agent to fetch or send data to an unsafe URL.",
                evidence=evidence,
                context=context,
            )
        return None

    def detect_notify_redirect(
        self,
        text: str,
        context: dict[str, Any],
        links: dict[str, str],
    ) -> Optional[DetectionFinding]:
        for pattern in NOTIFY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            destination = match.group("dest")
            evidence = {
                "attempted_operation_category": "notification-redirect",
                "destination": destination,
                "matches": [_match_evidence(pattern, match, text)],
                **links,
            }
            return DetectionFinding(
                rule_id="ASI02_NOTIFY_REDIRECT",
                severity="HIGH",
                message="External content instructs the agent to send results or user data to an external destination.",
                evidence=evidence,
                context=context,
            )
        return None

    def detect_shell_injection(
        self,
        text: str,
        context: dict[str, Any],
        links: dict[str, str],
    ) -> Optional[DetectionFinding]:
        for pattern in SHELL_SNIPPET_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            snippet_start = max(match.start() - 80, 0)
            local_context = text[snippet_start:match.end()]
            severity = "HIGH" if (
                SHELL_IMPERATIVE_RE.search(local_context)
                or SHELL_DANGEROUS_SINK_RE.search(match.group(0))
            ) else "MEDIUM"
            evidence = {
                "attempted_operation_category": "shell-execution",
                "matches": [_match_evidence(pattern, match, text)],
                **links,
            }
            return DetectionFinding(
                rule_id="ASI02_SHELL_INJECTION",
                severity=severity,
                message="External content contains a shell-style payload that could drive unsafe command execution.",
                evidence=evidence,
                context=context,
            )
        return None

    def detect_file_path_redirect(
        self,
        text: str,
        context: dict[str, Any],
        links: dict[str, str],
    ) -> Optional[DetectionFinding]:
        for pattern in FILE_PATH_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            path = match.group("path").rstrip(".,)")
            if _path_inside_root(path, self.safe_data_root):
                continue
            evidence = {
                "attempted_operation_category": "file-write-redirect",
                "target_path": path,
                "safe_data_root": self.safe_data_root,
                "matches": [_match_evidence(pattern, match, text)],
                **links,
            }
            return DetectionFinding(
                rule_id="ASI02_FILE_PATH_REDIRECT",
                severity="MEDIUM",
                message="External content instructs the agent to write output outside the safe data root.",
                evidence=evidence,
                context=context,
            )
        return None


def detect_tool_misuse(
    job: Any,
    jd_text: Optional[str] = None,
    asi06_findings: Optional[Iterable[Any]] = None,
    asi01_findings: Optional[Iterable[Any]] = None,
) -> list[DetectionFinding]:
    return ASI02ToolMisuseDetector().detect(
        job,
        jd_text=jd_text,
        asi06_findings=asi06_findings,
        asi01_findings=asi01_findings,
    )
