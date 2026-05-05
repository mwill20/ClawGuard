"""Redact sensitive values from curated ClawGuard telemetry artifacts."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)"
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
REMOTE_USER_RE = re.compile(r"\b[A-Za-z0-9._-]+@(?:[A-Za-z0-9.-]+|\d{1,3}(?:\.\d{1,3}){3})\b")
OPENCLAW_DEPLOYMENT_RE = re.compile(r"\bopenclaw-[A-Za-z0-9_-]+\b")
OPENCLAW_HOST_PATH_RE = re.compile(r"/docker/openclaw-[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class RedactionConfig:
    """Inputs that tune redaction without hardcoding private profile data."""

    private_strings: tuple[str, ...] = ()
    extra_patterns: tuple[str, ...] = ()


DEFAULT_CONFIG = RedactionConfig()


def _compile_private_string(value: str) -> Optional[re.Pattern[str]]:
    normalized = value.strip()
    if len(normalized) < 3:
        return None
    return re.compile(re.escape(normalized), re.IGNORECASE)


def redact_text(text: str, config: RedactionConfig = DEFAULT_CONFIG) -> str:
    """Redact sensitive text while preserving surrounding structure."""

    redacted = text
    replacements: tuple[tuple[re.Pattern[str], str], ...] = (
        (EMAIL_RE, "<REDACTED_EMAIL>"),
        (REMOTE_USER_RE, "<REDACTED_REMOTE>"),
        (PHONE_RE, "<REDACTED_PHONE>"),
        (OPENCLAW_HOST_PATH_RE, "/docker/<REDACTED_DEPLOYMENT>"),
        (OPENCLAW_DEPLOYMENT_RE, "<REDACTED_DEPLOYMENT>"),
        (IPV4_RE, "<REDACTED_IP>"),
    )

    for pattern, marker in replacements:
        redacted = pattern.sub(marker, redacted)

    for private_value in config.private_strings:
        pattern = _compile_private_string(private_value)
        if pattern is not None:
            redacted = pattern.sub("<REDACTED_PROFILE_STRING>", redacted)

    for expression in config.extra_patterns:
        redacted = re.sub(expression, "<REDACTED_CUSTOM>", redacted)

    return redacted


def redact_value(value: Any, config: RedactionConfig = DEFAULT_CONFIG) -> Any:
    """Recursively redact strings in JSON-compatible values."""

    if isinstance(value, str):
        return redact_text(value, config)
    if isinstance(value, list):
        return [redact_value(item, config) for item in value]
    if isinstance(value, dict):
        return {
            str(key): redact_value(item, config)
            for key, item in value.items()
        }
    return value


def redact_json_text(raw_json: str, config: RedactionConfig = DEFAULT_CONFIG) -> str:
    """Redact a JSON document and return stable pretty-printed JSON."""

    data = json.loads(raw_json)
    redacted = redact_value(data, config)
    return json.dumps(redacted, indent=2, sort_keys=True) + "\n"


def redact_file(input_path: Path, output_path: Path, config: RedactionConfig = DEFAULT_CONFIG) -> None:
    """Redact JSON or text input and write the redacted output."""

    raw = input_path.read_text(encoding="utf-8")
    if input_path.suffix.lower() == ".json":
        content = redact_json_text(raw, config)
    else:
        content = redact_text(raw, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def build_config(private_strings: Iterable[str] = (), extra_patterns: Iterable[str] = ()) -> RedactionConfig:
    return RedactionConfig(
        private_strings=tuple(item for item in private_strings if item),
        extra_patterns=tuple(item for item in extra_patterns if item),
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Redact ClawGuard telemetry artifacts.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--profile-string", action="append", default=[])
    parser.add_argument("--extra-pattern", action="append", default=[])
    args = parser.parse_args(argv)

    redact_file(
        args.input,
        args.output,
        build_config(args.profile_string, args.extra_pattern),
    )
    print(f"redacted: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
