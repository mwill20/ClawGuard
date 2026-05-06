#!/usr/bin/env python3
"""Validate synthetic ClawGuard runtime-event telemetry contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_VERSIONS = {"runtime-events/0.1"}
SESSION_ID_RE = re.compile(r"^digest-\d{8}T\d{6}-[0-9a-f]{8}$")
EVENT_TYPES = {
    "identity_context",
    "credential_use",
    "file_access",
    "network_egress",
    "process_exec",
    "container_action",
    "file_write",
    "policy_decision",
    "tool_call",
}
POLICY_DECISIONS = {"allow", "block", "observe", "review"}
REQUIREMENTS = {"asi03", "asi05"}

REQUIRED_TOP_LEVEL = {
    "schema_version": str,
    "generated_at": str,
    "agent_session_id": str,
    "events": list,
}

REQUIRED_EVENT_FIELDS = {
    "event_id": str,
    "event_time": str,
    "agent_session_id": str,
    "event_type": str,
    "actor": dict,
    "source": dict,
    "operation": str,
    "operation_category": str,
    "target": dict,
    "policy": dict,
    "correlation": dict,
    "evidence": dict,
}

FORBIDDEN_KEYS = {
    "api_key",
    "password",
    "raw_secret",
    "raw_token",
    "secret",
    "secret_value",
    "token",
    "token_value",
}
FORBIDDEN_STRING_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"),
]


class RuntimeEventValidationError(ValueError):
    """Raised when runtime-event telemetry violates the Phase 2 contract."""


def _expect_type(data: dict[str, Any], field: str, expected_type: type, path: str) -> None:
    if field not in data:
        raise RuntimeEventValidationError(f"{path}.{field} is missing")
    if not isinstance(data[field], expected_type):
        actual = type(data[field]).__name__
        raise RuntimeEventValidationError(f"{path}.{field} expected {expected_type.__name__}, got {actual}")


def _scan_for_sensitive_values(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lc = key.lower()
            if key_lc in FORBIDDEN_KEYS:
                raise RuntimeEventValidationError(f"{path}.{key} uses forbidden raw secret field name")
            _scan_for_sensitive_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_sensitive_values(item, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in FORBIDDEN_STRING_PATTERNS:
            if pattern.search(value):
                raise RuntimeEventValidationError(f"{path} appears to contain raw credential material")


def _require_event_classes(event_types: set[str], requirement: str) -> None:
    if requirement == "asi03":
        missing = {"identity_context", "credential_use"} - event_types
        if missing:
            raise RuntimeEventValidationError(
                f"ASI03 readiness requires event type(s): {', '.join(sorted(missing))}"
            )
        if not ({"file_access", "network_egress"} & event_types):
            raise RuntimeEventValidationError(
                "ASI03 readiness requires file_access or network_egress telemetry"
            )
    elif requirement == "asi05":
        missing = {"process_exec"} - event_types
        if missing:
            raise RuntimeEventValidationError(
                f"ASI05 readiness requires event type(s): {', '.join(sorted(missing))}"
            )
        if not ({"container_action", "file_write"} & event_types):
            raise RuntimeEventValidationError(
                "ASI05 readiness requires container_action or file_write telemetry"
            )
    else:
        raise RuntimeEventValidationError(f"unsupported readiness requirement: {requirement}")


def validate_runtime_events(data: dict[str, Any], require: list[str] | None = None) -> dict[str, Any]:
    for field, expected_type in REQUIRED_TOP_LEVEL.items():
        _expect_type(data, field, expected_type, "runtime_events")

    if data["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeEventValidationError(
            f"runtime_events.schema_version unsupported: {data['schema_version']}"
        )

    agent_session_id = data["agent_session_id"]
    if not SESSION_ID_RE.match(agent_session_id):
        raise RuntimeEventValidationError(
            f"runtime_events.agent_session_id has invalid format: {agent_session_id}"
        )

    _scan_for_sensitive_values(data, "runtime_events")

    event_type_counts: Counter[str] = Counter()
    policy_counts: Counter[str] = Counter()
    event_ids: set[str] = set()

    for index, event in enumerate(data["events"]):
        if not isinstance(event, dict):
            raise RuntimeEventValidationError(f"runtime_events.events[{index}] expected object")
        event_path = f"runtime_events.events[{index}]"
        for field, expected_type in REQUIRED_EVENT_FIELDS.items():
            _expect_type(event, field, expected_type, event_path)

        if event["event_id"] in event_ids:
            raise RuntimeEventValidationError(f"{event_path}.event_id is duplicated: {event['event_id']}")
        event_ids.add(event["event_id"])

        if event["agent_session_id"] != agent_session_id:
            raise RuntimeEventValidationError(f"{event_path}.agent_session_id does not match top-level session")
        if event["event_type"] not in EVENT_TYPES:
            raise RuntimeEventValidationError(f"{event_path}.event_type unsupported: {event['event_type']}")
        event_type_counts[event["event_type"]] += 1

        _expect_type(event["actor"], "type", str, f"{event_path}.actor")
        _expect_type(event["actor"], "id", str, f"{event_path}.actor")
        _expect_type(event["source"], "component", str, f"{event_path}.source")
        _expect_type(event["target"], "kind", str, f"{event_path}.target")
        _expect_type(event["target"], "label", str, f"{event_path}.target")
        _expect_type(event["target"], "redaction_status", str, f"{event_path}.target")
        _expect_type(event["policy"], "decision", str, f"{event_path}.policy")
        _expect_type(event["policy"], "reason", str, f"{event_path}.policy")
        _expect_type(event["correlation"], "agent_session_id", str, f"{event_path}.correlation")
        _expect_type(event["correlation"], "related_rule_ids", list, f"{event_path}.correlation")

        if event["policy"]["decision"] not in POLICY_DECISIONS:
            raise RuntimeEventValidationError(
                f"{event_path}.policy.decision unsupported: {event['policy']['decision']}"
            )
        policy_counts[event["policy"]["decision"]] += 1

        if event["correlation"]["agent_session_id"] != agent_session_id:
            raise RuntimeEventValidationError(
                f"{event_path}.correlation.agent_session_id does not match top-level session"
            )

    required = require or []
    for requirement in required:
        if requirement not in REQUIREMENTS:
            raise RuntimeEventValidationError(f"unsupported readiness requirement: {requirement}")
        _require_event_classes(set(event_type_counts), requirement)

    return {
        "agent_session_id": agent_session_id,
        "event_count": len(data["events"]),
        "event_type_counts": dict(sorted(event_type_counts.items())),
        "policy_decision_counts": dict(sorted(policy_counts.items())),
        "required_readiness": sorted(required),
        "schema_version": data["schema_version"],
        "status": "valid",
    }


def load_and_validate(path: Path, require: list[str] | None = None) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeEventValidationError("runtime_events root must be an object")
    return validate_runtime_events(data, require=require)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ClawGuard runtime-event telemetry shape.")
    parser.add_argument("--input", default="examples/runtime_events_minimal.json")
    parser.add_argument("--require", action="append", choices=sorted(REQUIREMENTS), default=[])
    args = parser.parse_args()

    try:
        result = load_and_validate(Path(args.input), require=args.require)
    except (json.JSONDecodeError, OSError, RuntimeEventValidationError) as exc:
        print(f"runtime event validation failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
