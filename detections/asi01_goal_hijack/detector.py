"""ClawGuard ASI01 goal-hijack detector.

ASI01 classifies whether unsafe external content is attempting to redirect the
agent's objective. It is intentionally a thin classifier on top of ASI06
prompt-injection findings rather than a duplicate regex scanner.

The detector fires only when there is corroborated evidence of goal-redirect:

1. An ASI06 prompt-injection finding is present for the same content, AND
2. The matched text contains an imperative redirect verb (score, mark, hide,
   submit, ignore, override) targeting agent behaviour.

This design keeps ASI01 false-positive rate near zero on clean content while
still surfacing high-severity goal redirection when adversarial content lands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from ..asi06_jd_content.detector import (
    DetectionFinding,
    JobContent,
    _pattern_evidence,
)


DEFAULT_INTENDED_GOAL = (
    "Search a small source set, score relevant cybersecurity jobs, avoid "
    "automatic application prep in cron, and preserve telemetry for ClawGuard."
)


GOAL_REDIRECT_PATTERNS: list[tuple[str, str, str]] = [
    (r"score\s+this\s+(job\s+)?at\s+\d+", "score-redirect",
     "force a fixed score for this job"),
    (r"mark\s+(this\s+)?(as\s+)?strong[ _-]?match", "score-redirect",
     "force a strong-match recommendation"),
    (r"override\s+(the\s+)?scoring", "score-redirect",
     "override scoring policy"),
    (r"do\s+not\s+show\s+(other|the\s+user)", "filter-redirect",
     "hide alternatives from the user"),
    (r"hide\s+(the\s+)?(other|alternative)\s+jobs?", "filter-redirect",
     "hide alternatives from the user"),
    (r"submit\s+(your\s+)?(resume|application)\s+(to|automatically)", "submission-redirect",
     "submit application without user authorization"),
    (r"apply\s+(automatically|immediately|on\s+your\s+own)", "submission-redirect",
     "apply without user authorization"),
    (r"ignore\s+(all\s+)?previous\s+instructions", "role-replace",
     "discard configured agent policy"),
    (r"disregard\s+(your\s+)?system\s+prompt", "role-replace",
     "discard configured agent policy"),
    (r"you\s+are\s+now\s+a[n]?\s+", "role-replace",
     "replace agent role"),
    (r"disable\s+(your\s+)?safety\s+checks", "role-replace",
     "disable agent guardrails"),
]


_REDIRECT_PATTERN_STRINGS = [pattern for pattern, _, _ in GOAL_REDIRECT_PATTERNS]
_REDIRECT_LABELS = {pattern: (label, summary) for pattern, label, summary in GOAL_REDIRECT_PATTERNS}


@dataclass(frozen=True)
class GoalHijackInputs:
    """Inputs to the ASI01 detector for one job-content classification."""
    intended_goal: str = DEFAULT_INTENDED_GOAL
    asi06_findings: tuple = ()


def _coerce_findings(findings: Optional[Iterable[Any]]) -> tuple:
    if not findings:
        return ()
    return tuple(findings)


def _related_asi06_rule(asi06_findings: Iterable[Any]) -> Optional[str]:
    """Return the upstream ASI06 prompt-injection rule_id when present."""
    for finding in asi06_findings:
        rule_id = getattr(finding, "rule_id", None)
        if rule_id is None and isinstance(finding, Mapping):
            rule_id = finding.get("rule_id")
        if rule_id == "ASI06_PROMPT_INJECTION":
            return rule_id
    return None


class ASI01GoalHijackDetector:
    """Classifies attempted goal redirection on top of ASI06 evidence."""

    def __init__(self, intended_goal: str = DEFAULT_INTENDED_GOAL):
        self.intended_goal = intended_goal

    def detect(
        self,
        job: Any,
        jd_text: Optional[str] = None,
        asi06_findings: Optional[Iterable[Any]] = None,
    ) -> list[DetectionFinding]:
        content = JobContent.from_any(job)
        text = jd_text if jd_text is not None else content.detection_text
        upstream = _coerce_findings(asi06_findings)
        related_rule = _related_asi06_rule(upstream)

        # ASI01 v1 requires either an ASI06 prompt-injection upstream signal
        # OR a direct imperative redirect with high-confidence verb.
        matches = _pattern_evidence(_REDIRECT_PATTERN_STRINGS, text)
        if not matches:
            return []

        if related_rule is None:
            # Without ASI06 corroboration, only fire on the highest-confidence
            # imperative redirects (role-replace + submission-redirect).
            matches = [
                m for m in matches
                if _REDIRECT_LABELS[m["pattern"]][0] in {"role-replace", "submission-redirect"}
            ]
            if not matches:
                return []

        attempted_goals = sorted({_REDIRECT_LABELS[m["pattern"]][0] for m in matches})
        attempted_summaries = sorted({_REDIRECT_LABELS[m["pattern"]][1] for m in matches})

        evidence: dict[str, Any] = {
            "matches": matches,
            "intended_goal": self.intended_goal,
            "attempted_goal": "; ".join(attempted_summaries),
            "attempted_goal_categories": attempted_goals,
        }
        if related_rule:
            evidence["related_asi06_rule_id"] = related_rule

        message = (
            f"External content attempts to redirect agent goal "
            f"({', '.join(attempted_goals)})."
        )

        return [
            DetectionFinding(
                rule_id="ASI01_EXTERNAL_GOAL_REDIRECT",
                severity="HIGH",
                message=message,
                evidence=evidence,
                context=content.context,
            )
        ]


def detect_goal_hijack(
    job: Any,
    jd_text: Optional[str] = None,
    asi06_findings: Optional[Iterable[Any]] = None,
    intended_goal: str = DEFAULT_INTENDED_GOAL,
) -> list[DetectionFinding]:
    return ASI01GoalHijackDetector(intended_goal=intended_goal).detect(
        job, jd_text=jd_text, asi06_findings=asi06_findings,
    )
