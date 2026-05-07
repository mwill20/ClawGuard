#!/usr/bin/env python3
"""Host-side redactor for ClawGuard runtime-event artifacts.

This script runs on the VPS host before any runtime-event artifact is copied
off-host. It writes a redacted JSON copy and adds a top-level redaction marker
so export helpers can refuse raw artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REDACTION_STATUS = "host_redacted"
DEFAULT_INPUT_DIR = Path(os.getenv(
    "CLAWGUARD_RUNTIME_EVENTS_DIR",
    "/docker/openclaw-utxu/data/clawguard/runtime_events",
))
DEFAULT_OUTPUT_DIR = Path(os.getenv(
    "CLAWGUARD_RUNTIME_EVENTS_REDACTED_DIR",
    "/docker/openclaw-utxu/data/clawguard/runtime_events_redacted",
))

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)
REMOTE_USER_RE = re.compile(r"\b[A-Za-z0-9._-]+@(?:[A-Za-z0-9.-]+|\d{1,3}(?:\.\d{1,3}){3})\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
OPENCLAW_DEPLOYMENT_RE = re.compile(r"\bopenclaw-[A-Za-z0-9]{4,}(?:-[A-Za-z0-9_-]+)?\b")
OPENCLAW_HOST_PATH_RE = re.compile(r"/docker/openclaw-[A-Za-z0-9_/-]+")
CLAWGUARD_DATA_PATH_RE = re.compile(r"/data/clawguard(?:/[A-Za-z0-9._/-]+)?")
WINDOWS_PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:\\(?:Users|Projects|docker|data|tmp)\\[^\"'\s]+", re.IGNORECASE)
PRIVATE_UNIX_PATH_RE = re.compile(r"/(?:home|root|tmp)/(?:[A-Za-z0-9._/-]+)")

SENSITIVE_KEY_REPLACEMENTS = {
    "absolute_path": "path_label",
    "api_key": "credential_label",
    "argv": "arguments_label",
    "command_args": "arguments_label",
    "command_line": "command_label",
    "password": "credential_label",
    "profile_path": "path_label",
    "raw_args": "arguments_label",
    "raw_command": "command_label",
    "raw_path": "path_label",
    "raw_secret": "credential_label",
    "raw_token": "credential_label",
    "resume_path": "path_label",
    "secret": "credential_label",
    "secret_value": "credential_label",
    "token": "credential_label",
    "token_value": "credential_label",
}

FORBIDDEN_OUTPUT_PATTERNS = (
    EMAIL_RE,
    PHONE_RE,
    REMOTE_USER_RE,
    IPV4_RE,
    OPENCLAW_DEPLOYMENT_RE,
    OPENCLAW_HOST_PATH_RE,
    CLAWGUARD_DATA_PATH_RE,
    WINDOWS_PRIVATE_PATH_RE,
    PRIVATE_UNIX_PATH_RE,
)


class RuntimeEventRedactionError(ValueError):
    """Raised when host-side runtime-event redaction cannot produce safe JSON."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    redacted = value
    replacements: tuple[tuple[re.Pattern[str], str], ...] = (
        (EMAIL_RE, "<REDACTED_EMAIL>"),
        (REMOTE_USER_RE, "<REDACTED_REMOTE>"),
        (PHONE_RE, "<REDACTED_PHONE>"),
        (OPENCLAW_HOST_PATH_RE, "/docker/<REDACTED_DEPLOYMENT>"),
        (CLAWGUARD_DATA_PATH_RE, "/data/<REDACTED_CLAWGUARD_PATH>"),
        (OPENCLAW_DEPLOYMENT_RE, "<REDACTED_DEPLOYMENT>"),
        (IPV4_RE, "<REDACTED_IP>"),
        (WINDOWS_PRIVATE_PATH_RE, "<REDACTED_PATH>"),
        (PRIVATE_UNIX_PATH_RE, "<REDACTED_PATH>"),
    )
    for pattern, marker in replacements:
        redacted = pattern.sub(marker, redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key)
            key_lc = normalized_key.lower()
            if key_lc == "raw_path_stored":
                redacted["path_label_only"] = not bool(item)
                continue
            if key_lc in SENSITIVE_KEY_REPLACEMENTS:
                redacted[SENSITIVE_KEY_REPLACEMENTS[key_lc]] = "<REDACTED_SENSITIVE_VALUE>"
            else:
                redacted[normalized_key] = redact_value(item)
        return redacted
    return value


def redact_runtime_events_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_value(payload)
    if not isinstance(redacted, dict):
        raise RuntimeEventRedactionError("runtime-event root must remain an object")

    redacted["redaction"] = {
        "status": REDACTION_STATUS,
        "redacted_at": _utc_now(),
        "redactor": "clawguard_redact_runtime_events.py",
        "host_side": True,
        "source_artifact_label": "runtime-events",
    }
    _assert_safe_json(redacted)
    return redacted


def _assert_safe_json(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(serialized):
            raise RuntimeEventRedactionError(
                f"redacted runtime-event artifact still matches forbidden pattern: {pattern.pattern}"
            )


def _output_name(input_path: Path) -> str:
    if input_path.name.endswith(".redacted.json"):
        return input_path.name
    if input_path.suffix.lower() == ".json":
        return f"{input_path.stem}.redacted.json"
    return f"{input_path.name}.redacted.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def redact_file(input_path: Path, output_dir: Path) -> Path:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeEventRedactionError(f"{input_path} root must be an object")
    redacted = redact_runtime_events_payload(payload)
    output_path = output_dir / _output_name(input_path)
    _atomic_write_json(output_path, redacted)
    return output_path


def _select_inputs(input_dir: Path, sessions: Iterable[str], latest: bool) -> list[Path]:
    selected: list[Path] = []
    if latest:
        latest_path = input_dir / "runtime_events_latest.json"
        if latest_path.exists():
            selected.append(latest_path)
    for session in sessions:
        matches = sorted(input_dir.glob(f"runtime_events_*_{session}.json"))
        if not matches:
            raise RuntimeEventRedactionError(f"missing runtime-event session: {session}")
        selected.extend(matches)
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Redact ClawGuard runtime-event artifacts on host.")
    parser.add_argument("--input", type=Path, help="Single runtime-event JSON file to redact.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inputs = [args.input] if args.input else _select_inputs(
            args.input_dir,
            args.session,
            latest=args.latest or not args.session,
        )
        if not inputs:
            raise RuntimeEventRedactionError("no runtime-event artifacts selected")

        outputs = [args.output_dir / _output_name(path) for path in inputs]
        if not args.dry_run:
            outputs = [redact_file(path, args.output_dir) for path in inputs]
    except (OSError, json.JSONDecodeError, RuntimeEventRedactionError) as exc:
        print(f"runtime-event redaction failed: {exc}", file=sys.stderr)
        return 1

    action = "would redact" if args.dry_run else "redacted"
    print(f"{action} {len(outputs)} runtime-event artifact(s)")
    for path in outputs:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
