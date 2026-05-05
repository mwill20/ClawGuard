#!/usr/bin/env python3
"""Validate ClawGuard post-compile telemetry JSON shape."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SESSION_ID_RE = re.compile(r"^digest-\d{8}T\d{6}-[0-9a-f]{8}$")
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2"}
DEFAULT_LEGACY_SCHEMA_VERSION = "1.0"

REQUIRED_TOP_LEVEL = {
    "schema_version": str,
    "generated_at": str,
    "digest_path": str,
    "agent_session_id": str,
    "finding_count": int,
    "rule_counts": dict,
    "severity_counts": dict,
    "finding_source_platform_counts": dict,
    "digest_top_match_source_counts": dict,
    "digest_summary": dict,
    "findings": list,
}

REQUIRED_DIGEST_SUMMARY = {
    "total_found": int,
    "new_jobs": int,
    "auto_prepared": int,
    "credits_used_today": int,
}

REQUIRED_FINDING_FIELDS = {
    "job_id": str,
    "agent_session_id": str,
    "rule_id": str,
    "severity": str,
    "message": str,
    "evidence": dict,
    "context": dict,
    "detected_at": str,
}

REQUIRED_ASI01_EVIDENCE_FIELDS = {
    "attempted_goal": str,
    "attempted_goal_categories": list,
    "intended_goal": str,
    "matches": list,
}

REQUIRED_ASI02_EVIDENCE_FIELDS = {
    "attempted_operation_category": str,
    "matches": list,
}


class TelemetryValidationError(ValueError):
    """Raised when telemetry does not match the expected ClawGuard shape."""


def _expect_type(data: dict[str, Any], field: str, expected_type: type, path: str) -> None:
    if field not in data:
        raise TelemetryValidationError(f"{path}.{field} is missing")
    if not isinstance(data[field], expected_type):
        actual = type(data[field]).__name__
        raise TelemetryValidationError(f"{path}.{field} expected {expected_type.__name__}, got {actual}")


def validate_telemetry(data: dict[str, Any]) -> dict[str, Any]:
    schema_version = data.get("schema_version", DEFAULT_LEGACY_SCHEMA_VERSION)
    if not isinstance(schema_version, str):
        raise TelemetryValidationError("telemetry.schema_version expected str")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise TelemetryValidationError(
            f"telemetry.schema_version unsupported: {schema_version}"
        )

    required_top_level = dict(REQUIRED_TOP_LEVEL)
    if "schema_version" not in data and schema_version == DEFAULT_LEGACY_SCHEMA_VERSION:
        # Legacy Phase 1 telemetry samples predate the explicit top-level field.
        required_top_level.pop("schema_version")

    for field, expected_type in required_top_level.items():
        _expect_type(data, field, expected_type, "telemetry")

    agent_session_id = data["agent_session_id"]
    if not SESSION_ID_RE.match(agent_session_id):
        raise TelemetryValidationError(f"telemetry.agent_session_id has invalid format: {agent_session_id}")

    for field, expected_type in REQUIRED_DIGEST_SUMMARY.items():
        _expect_type(data["digest_summary"], field, expected_type, "telemetry.digest_summary")

    findings = data["findings"]
    if data["finding_count"] != len(findings):
        raise TelemetryValidationError(
            f"telemetry.finding_count expected {len(findings)} from findings length, got {data['finding_count']}"
        )

    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise TelemetryValidationError(f"telemetry.findings[{index}] expected object")
        for field, expected_type in REQUIRED_FINDING_FIELDS.items():
            _expect_type(finding, field, expected_type, f"telemetry.findings[{index}]")
        if finding["agent_session_id"] != agent_session_id:
            raise TelemetryValidationError(
                f"telemetry.findings[{index}].agent_session_id does not match top-level session"
            )
        if schema_version == "1.0" and finding["rule_id"].startswith("ASI01_"):
            raise TelemetryValidationError(
                f"telemetry.findings[{index}] has ASI01 finding but schema_version is 1.0"
            )
        if schema_version in {"1.1", "1.2"} and finding["rule_id"].startswith("ASI01_"):
            for field, expected_type in REQUIRED_ASI01_EVIDENCE_FIELDS.items():
                _expect_type(
                    finding["evidence"],
                    field,
                    expected_type,
                    f"telemetry.findings[{index}].evidence",
                )
        if schema_version in {"1.0", "1.1"} and finding["rule_id"].startswith("ASI02_"):
            raise TelemetryValidationError(
                f"telemetry.findings[{index}] has ASI02 finding but schema_version is {schema_version}"
            )
        if schema_version == "1.2" and finding["rule_id"].startswith("ASI02_"):
            for field, expected_type in REQUIRED_ASI02_EVIDENCE_FIELDS.items():
                _expect_type(
                    finding["evidence"],
                    field,
                    expected_type,
                    f"telemetry.findings[{index}].evidence",
                )

    expected_rule_counts = dict(sorted(Counter(finding["rule_id"] for finding in findings).items()))
    expected_severity_counts = dict(sorted(Counter(finding["severity"] for finding in findings).items()))
    expected_source_counts = dict(
        sorted(Counter(finding["context"].get("source_platform", "unknown") for finding in findings).items())
    )

    if data["rule_counts"] != expected_rule_counts:
        raise TelemetryValidationError("telemetry.rule_counts does not match findings")
    if data["severity_counts"] != expected_severity_counts:
        raise TelemetryValidationError("telemetry.severity_counts does not match findings")
    if data["finding_source_platform_counts"] != expected_source_counts:
        raise TelemetryValidationError("telemetry.finding_source_platform_counts does not match findings")

    return {
        "agent_session_id": agent_session_id,
        "finding_count": data["finding_count"],
        "rule_count_keys": sorted(data["rule_counts"].keys()),
        "schema_version": schema_version,
        "status": "valid",
    }


def load_and_validate(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TelemetryValidationError("telemetry root must be an object")
    return validate_telemetry(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ClawGuard telemetry JSON shape.")
    parser.add_argument("--input", default="examples/telemetry_sample.json")
    args = parser.parse_args()

    try:
        result = load_and_validate(Path(args.input))
    except (json.JSONDecodeError, OSError, TelemetryValidationError) as exc:
        print(f"telemetry validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
