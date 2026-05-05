"""Select ClawGuard telemetry sessions that need review.

The selector intentionally parses telemetry JSON instead of shell-grepping
logs. It can run against a local directory of pulled telemetry files or on the
operational host before a human-triggered export.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class TelemetrySession:
    """Normalized subset used by the review selector."""

    session_id: str
    path: Path
    generated_at: Optional[datetime]
    finding_count: int
    rule_ids: frozenset[str]
    schema_version: str


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Expected YYYY-MM-DD date, got {value!r}"
        ) from exc


def _parse_generated_at(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.removesuffix("Z")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _finding_count(payload: dict[str, Any]) -> int:
    value = payload.get("finding_count")
    if isinstance(value, int):
        return value
    findings = payload.get("findings")
    if isinstance(findings, list):
        return len(findings)
    return 0


def _rule_ids(payload: dict[str, Any]) -> frozenset[str]:
    rules: set[str] = set()
    rule_counts = payload.get("rule_counts")
    if isinstance(rule_counts, dict):
        rules.update(str(rule_id) for rule_id in rule_counts.keys())

    findings = payload.get("findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, dict) and finding.get("rule_id"):
                rules.add(str(finding["rule_id"]))

    return frozenset(rules)


def load_sessions(telemetry_dir: Path) -> list[TelemetrySession]:
    """Load valid telemetry JSON files from a directory.

    Non-telemetry JSON files are skipped so the helper can safely run against
    broad directories such as `examples/`.
    """

    sessions: dict[str, TelemetrySession] = {}
    for path in sorted(telemetry_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(payload, dict):
            continue
        session_id = payload.get("agent_session_id")
        if not isinstance(session_id, str) or not session_id:
            continue

        session = TelemetrySession(
            session_id=session_id,
            path=path,
            generated_at=_parse_generated_at(payload.get("generated_at")),
            finding_count=_finding_count(payload),
            rule_ids=_rule_ids(payload),
            schema_version=str(payload.get("schema_version", "1.0")),
        )

        existing = sessions.get(session_id)
        if existing is None or path.name != "telemetry_latest.json":
            sessions[session_id] = session

    return list(sessions.values())


def select_sessions(
    sessions: Iterable[TelemetrySession],
    *,
    rule: Optional[str] = None,
    finding_count_min: Optional[int] = None,
    finding_count_max: Optional[int] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
    baseline: bool = False,
) -> list[TelemetrySession]:
    """Return sessions matching review criteria."""

    selected: list[TelemetrySession] = []
    for session in sessions:
        session_date = session.generated_at.date() if session.generated_at else None
        if rule and rule not in session.rule_ids:
            continue
        if finding_count_min is not None and session.finding_count < finding_count_min:
            continue
        if finding_count_max is not None and session.finding_count > finding_count_max:
            continue
        if baseline and session.finding_count != 0:
            continue
        if since and (session_date is None or session_date < since):
            continue
        if until and (session_date is None or session_date > until):
            continue
        selected.append(session)

    return sorted(
        selected,
        key=lambda item: (item.generated_at or datetime.min, item.session_id),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select ClawGuard telemetry sessions for curated review."
    )
    parser.add_argument("--telemetry-dir", required=True, type=Path)
    parser.add_argument("--rule", help="Only include sessions containing this rule_id.")
    parser.add_argument("--finding-count-min", type=int)
    parser.add_argument("--finding-count-max", type=int)
    parser.add_argument(
        "--since",
        type=_parse_date,
        help="Only include sessions generated on or after YYYY-MM-DD.",
    )
    parser.add_argument(
        "--until",
        type=_parse_date,
        help="Only include sessions generated on or before YYYY-MM-DD.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Only include clean sessions with zero findings.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.telemetry_dir.exists() or not args.telemetry_dir.is_dir():
        print(
            f"Telemetry directory not found: {args.telemetry_dir}",
            file=sys.stderr,
        )
        return 2

    sessions = load_sessions(args.telemetry_dir)
    selected = select_sessions(
        sessions,
        rule=args.rule,
        finding_count_min=args.finding_count_min,
        finding_count_max=args.finding_count_max,
        since=args.since,
        until=args.until,
        baseline=args.baseline,
    )

    for session in selected:
        print(session.session_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
