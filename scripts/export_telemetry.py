"""Curate pulled ClawGuard telemetry into repo lesson artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from scripts import telemetry_redaction, validate_telemetry
except ImportError:  # pragma: no cover - supports direct script execution
    import telemetry_redaction  # type: ignore
    import validate_telemetry  # type: ignore


@dataclass(frozen=True)
class TelemetryExportCandidate:
    session_id: str
    json_path: Path
    md_path: Optional[Path]
    payload: dict[str, Any]


def _generated_month(payload: dict[str, Any]) -> str:
    generated_at = payload.get("generated_at")
    if isinstance(generated_at, str):
        try:
            return datetime.fromisoformat(generated_at.removesuffix("Z")).strftime("%Y-%m")
        except ValueError:
            pass
    digest_path = str(payload.get("digest_path", ""))
    for token in digest_path.replace("_", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            # Fall through to the filename parser below; this avoids treating a
            # bare year as a month.
            break
    return "unknown-month"


def _candidate_md_path(json_path: Path) -> Optional[Path]:
    md_path = json_path.with_suffix(".md")
    if md_path.exists():
        return md_path
    if json_path.name == "telemetry_latest.json":
        latest_md = json_path.parent / "telemetry_latest.md"
        if latest_md.exists():
            return latest_md
    return None


def load_candidates(input_dir: Path) -> dict[str, TelemetryExportCandidate]:
    candidates: dict[str, TelemetryExportCandidate] = {}
    for json_path in sorted(input_dir.glob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        session_id = payload.get("agent_session_id")
        if not isinstance(session_id, str) or not session_id:
            continue

        candidate = TelemetryExportCandidate(
            session_id=session_id,
            json_path=json_path,
            md_path=_candidate_md_path(json_path),
            payload=payload,
        )
        existing = candidates.get(session_id)
        if existing is None or json_path.name != "telemetry_latest.json":
            candidates[session_id] = candidate
    return candidates


def _selected_candidates(
    candidates: dict[str, TelemetryExportCandidate],
    sessions: Optional[list[str]],
) -> list[TelemetryExportCandidate]:
    if not sessions:
        return sorted(candidates.values(), key=lambda candidate: candidate.session_id)

    missing = [session for session in sessions if session not in candidates]
    if missing:
        raise ValueError(f"Missing telemetry session(s): {', '.join(missing)}")
    return [candidates[session] for session in sessions]


def _redacted_payload(
    payload: dict[str, Any],
    config: telemetry_redaction.RedactionConfig,
) -> dict[str, Any]:
    redacted = telemetry_redaction.redact_value(payload, config)
    if not isinstance(redacted, dict):
        raise ValueError("Redacted telemetry root must remain an object")
    if "schema_version" not in redacted:
        redacted = dict(redacted)
        redacted["schema_version"] = validate_telemetry.DEFAULT_LEGACY_SCHEMA_VERSION
    validate_telemetry.validate_telemetry(redacted)
    return redacted


def _write_month_index(month_dir: Path) -> None:
    rows: list[tuple[str, str, int, str]] = []
    for session_dir in sorted(path for path in month_dir.iterdir() if path.is_dir()):
        telemetry_json = session_dir / "telemetry.json"
        if not telemetry_json.exists():
            continue
        payload = json.loads(telemetry_json.read_text(encoding="utf-8"))
        rows.append(
            (
                str(payload.get("agent_session_id", session_dir.name)),
                str(payload.get("schema_version", "1.0")),
                int(payload.get("finding_count", 0)),
                str(payload.get("generated_at", "")),
            )
        )

    lines = [
        f"# ClawGuard Telemetry Index - {month_dir.name}",
        "",
        "| Session | Schema | Findings | Generated | Reviewer notes |",
        "|---|---:|---:|---|---|",
    ]
    for session_id, schema_version, finding_count, generated_at in rows:
        lines.append(
            f"| [{session_id}]({session_id}/telemetry.json) | {schema_version} | "
            f"{finding_count} | {generated_at} |  |"
        )
    month_dir.mkdir(parents=True, exist_ok=True)
    (month_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_candidates(
    candidates: list[TelemetryExportCandidate],
    output_dir: Path,
    config: telemetry_redaction.RedactionConfig,
    *,
    dry_run: bool = False,
) -> list[Path]:
    exported: list[Path] = []
    for candidate in candidates:
        redacted_payload = _redacted_payload(candidate.payload, config)
        month = _generated_month(redacted_payload)
        session_dir = output_dir / month / candidate.session_id
        exported.append(session_dir)

        if dry_run:
            continue

        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "telemetry.json").write_text(
            json.dumps(redacted_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if candidate.md_path:
            md_text = candidate.md_path.read_text(encoding="utf-8")
            redacted_md = telemetry_redaction.redact_text(md_text, config)
        else:
            redacted_md = (
                f"# ClawGuard Telemetry Summary\n\n"
                f"- Agent session: `{candidate.session_id}`\n"
                f"- Finding count: `{redacted_payload.get('finding_count', 0)}`\n"
            )
        (session_dir / "telemetry.md").write_text(redacted_md, encoding="utf-8")

    if not dry_run:
        for month_dir in sorted({path.parent for path in exported}):
            _write_month_index(month_dir)

    return exported


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redact and curate pulled ClawGuard telemetry artifacts."
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("lessons/telemetry"), type=Path)
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--profile-string", action="append", default=[])
    parser.add_argument("--extra-pattern", action="append", default=[])
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_dir.exists() or not args.input_dir.is_dir():
        print(f"Input directory not found: {args.input_dir}", file=sys.stderr)
        return 2

    try:
        candidates = _selected_candidates(load_candidates(args.input_dir), args.session)
        exported = export_candidates(
            candidates,
            args.output_dir,
            telemetry_redaction.build_config(args.profile_string, args.extra_pattern),
            dry_run=args.dry_run,
        )
    except (ValueError, validate_telemetry.TelemetryValidationError) as exc:
        print(f"telemetry export failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"DRY RUN: would export {len(exported)} telemetry session(s)")
    else:
        print(f"Exported {len(exported)} telemetry session(s)")
    for path in exported:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
