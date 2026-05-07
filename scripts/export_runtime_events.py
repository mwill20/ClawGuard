"""Curate host-redacted ClawGuard runtime-event artifacts into lesson assets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from scripts import validate_runtime_events
except ImportError:  # pragma: no cover - supports direct script execution
    import validate_runtime_events  # type: ignore


REQUIRED_REDACTION_STATUS = "host_redacted"


class RuntimeEventExportError(ValueError):
    """Raised when a runtime-event artifact is not safe to export."""


@dataclass(frozen=True)
class RuntimeEventExportCandidate:
    session_id: str
    json_path: Path
    payload: dict[str, Any]
    validation: dict[str, Any]


def _generated_month(payload: dict[str, Any]) -> str:
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str):
        try:
            return datetime.fromisoformat(generated_at.removesuffix("Z")).strftime("%Y-%m")
        except ValueError:
            pass
    return "unknown-month"


def _require_host_redaction(payload: dict[str, Any], path: Path) -> None:
    redaction = payload.get("redaction")
    if not isinstance(redaction, dict):
        raise RuntimeEventExportError(f"{path} missing top-level redaction metadata")
    if redaction.get("status") != REQUIRED_REDACTION_STATUS:
        raise RuntimeEventExportError(
            f"{path} redaction.status must be {REQUIRED_REDACTION_STATUS}"
        )


def load_candidates(input_dir: Path) -> dict[str, RuntimeEventExportCandidate]:
    candidates: dict[str, RuntimeEventExportCandidate] = {}
    for json_path in sorted(input_dir.glob("*.redacted.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        _require_host_redaction(payload, json_path)
        validation = validate_runtime_events.validate_runtime_events(payload)
        session_id = validation["agent_session_id"]
        candidate = RuntimeEventExportCandidate(
            session_id=session_id,
            json_path=json_path,
            payload=payload,
            validation=validation,
        )
        existing = candidates.get(session_id)
        if existing is None or json_path.name != "runtime_events_latest.redacted.json":
            candidates[session_id] = candidate
    return candidates


def _selected_candidates(
    candidates: dict[str, RuntimeEventExportCandidate],
    sessions: Optional[list[str]],
) -> list[RuntimeEventExportCandidate]:
    if not sessions:
        return sorted(candidates.values(), key=lambda candidate: candidate.session_id)

    missing = [session for session in sessions if session not in candidates]
    if missing:
        raise RuntimeEventExportError(f"Missing runtime-event session(s): {', '.join(missing)}")
    return [candidates[session] for session in sessions]


def _reviewer_notes(payload: dict[str, Any]) -> str:
    event_types = {
        str(event.get("event_type", "unknown"))
        for event in payload.get("events", [])
        if isinstance(event, dict)
    }
    if {"process_exec", "container_action"}.issubset(event_types):
        return (
            "Clean real no-notify provider baseline with ASI03 and ASI05 "
            "readiness coverage; observe-only, no findings promoted."
        )
    if {"credential_use", "network_egress"}.issubset(event_types):
        return (
            "Clean real provider baseline with ASI03 readiness coverage; "
            "observe-only, no findings promoted."
        )
    return "Clean observe-only runtime baseline; no findings promoted."


def _write_month_index(month_dir: Path) -> None:
    rows: list[tuple[str, str, int, str, str, str]] = []
    for session_dir in sorted(path for path in month_dir.iterdir() if path.is_dir()):
        runtime_json = session_dir / "runtime_events.json"
        if not runtime_json.exists():
            continue
        payload = json.loads(runtime_json.read_text(encoding="utf-8"))
        rows.append(
            (
                str(payload.get("agent_session_id", session_dir.name)),
                str(payload.get("schema_version", "")),
                len(payload.get("events", []) or []),
                str(payload.get("generated_at", "")),
                str((payload.get("redaction") or {}).get("status", "")),
                _reviewer_notes(payload),
            )
        )

    lines = [
        f"# ClawGuard Runtime Events Index - {month_dir.name}",
        "",
        "| Session | Schema | Events | Generated | Redaction | Reviewer notes |",
        "|---|---:|---:|---|---|---|",
    ]
    for session_id, schema_version, event_count, generated_at, redaction_status, reviewer_notes in rows:
        lines.append(
            f"| [{session_id}]({session_id}/runtime_events.json) | {schema_version} | "
            f"{event_count} | {generated_at} | {redaction_status} | {reviewer_notes} |"
        )
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_markdown(candidate: RuntimeEventExportCandidate) -> str:
    counts = Counter(event.get("event_type", "unknown") for event in candidate.payload.get("events", []))
    lines = [
        "# ClawGuard Runtime Event Baseline",
        "",
        f"- Agent session: `{candidate.session_id}`",
        f"- Schema: `{candidate.payload.get('schema_version')}`",
        f"- Generated: `{candidate.payload.get('generated_at')}`",
        f"- Redaction status: `{(candidate.payload.get('redaction') or {}).get('status')}`",
        f"- Event count: `{sum(counts.values())}`",
        "",
        "## Event Counts",
        "",
    ]
    for event_type, count in sorted(counts.items()):
        lines.append(f"- `{event_type}`: `{count}`")
    lines.extend([
        "",
        "## Reviewer Notes",
        "",
        _reviewer_notes(candidate.payload),
    ])
    return "\n".join(lines) + "\n"


def export_candidates(
    candidates: list[RuntimeEventExportCandidate],
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> list[Path]:
    exported: list[Path] = []
    for candidate in candidates:
        month = _generated_month(candidate.payload)
        session_dir = output_dir / month / candidate.session_id
        exported.append(session_dir)
        if dry_run:
            continue

        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "runtime_events.json").write_text(
            json.dumps(candidate.payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (session_dir / "runtime_events.md").write_text(
            _summary_markdown(candidate),
            encoding="utf-8",
        )

    if not dry_run:
        for month_dir in sorted({path.parent for path in exported}):
            _write_month_index(month_dir)
    return exported


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and curate host-redacted ClawGuard runtime-event artifacts."
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("lessons/runtime-events"), type=Path)
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        print(f"Input directory not found: {args.input_dir}", file=sys.stderr)
        return 2

    try:
        candidates = _selected_candidates(load_candidates(args.input_dir), args.session)
        exported = export_candidates(candidates, args.output_dir, dry_run=args.dry_run)
    except (RuntimeEventExportError, validate_runtime_events.RuntimeEventValidationError) as exc:
        print(f"runtime-event export failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"DRY RUN: would export {len(exported)} runtime-event session(s)")
    else:
        print(f"Exported {len(exported)} runtime-event session(s)")
    for path in exported:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
