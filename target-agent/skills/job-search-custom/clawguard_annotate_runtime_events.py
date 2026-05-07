#!/usr/bin/env python3
"""Host-side annotator for ClawGuard runtime-event artifacts.

The OpenClaw Python runtime emits agent-side events inside the container. This
host helper appends label-only wrapper facts after cron/deploy commands finish,
so ASI05 can learn normal process/container behavior without raw command lines.
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
from typing import Any


ANNOTATOR_VERSION = "0.1"
DEFAULT_RUNTIME_FILE = Path(os.getenv(
    "CLAWGUARD_RUNTIME_EVENTS_LATEST",
    "/docker/openclaw-utxu/data/clawguard/runtime_events/runtime_events_latest.json",
))
SESSION_ID_RE = re.compile(r"^digest-\d{8}T\d{6}-[0-9a-f]{8}$")
SAFE_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,80}$")


class RuntimeEventAnnotationError(ValueError):
    """Raised when runtime-event host annotation cannot be safely applied."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_label(value: str, field_name: str) -> str:
    if not SAFE_LABEL_RE.match(value):
        raise RuntimeEventAnnotationError(f"{field_name} must be a label, got: {value!r}")
    return value


def _load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeEventAnnotationError("runtime-event artifact root must be an object")
    if payload.get("schema_version") != "runtime-events/0.1":
        raise RuntimeEventAnnotationError("runtime-event schema_version must be runtime-events/0.1")
    session_id = payload.get("agent_session_id")
    if not isinstance(session_id, str) or not SESSION_ID_RE.match(session_id):
        raise RuntimeEventAnnotationError("runtime-event artifact has invalid agent_session_id")
    events = payload.get("events")
    if not isinstance(events, list):
        raise RuntimeEventAnnotationError("runtime-event artifact events must be a list")
    return payload


def _archive_path_for_payload(latest_path: Path, payload: dict[str, Any]) -> Path:
    generated_at = str(payload.get("generated_at", ""))
    session_date = generated_at[:10] if len(generated_at) >= 10 else "unknown-date"
    return latest_path.parent / f"runtime_events_{session_date}_{payload['agent_session_id']}.json"


def _event_id(payload: dict[str, Any], operation: str, sequence_offset: int) -> str:
    return f"evt-{payload['agent_session_id']}-{operation}-{len(payload['events']) + sequence_offset:03d}"


def _base_event(
    payload: dict[str, Any],
    *,
    event_type: str,
    actor_id: str,
    operation: str,
    operation_category: str,
    target_kind: str,
    target_label: str,
    policy_decision: str,
    policy_reason: str,
    evidence: dict[str, Any],
    sequence_offset: int,
) -> dict[str, Any]:
    session_id = payload["agent_session_id"]
    return {
        "event_id": _event_id(payload, operation, sequence_offset),
        "event_time": _utc_now(),
        "agent_session_id": session_id,
        "event_type": event_type,
        "actor": {
            "type": "automation",
            "id": actor_id,
        },
        "source": {
            "component": "staggered_cron.sh",
            "code_path": "target-agent/skills/job-search-custom/staggered_cron.sh",
        },
        "operation": operation,
        "operation_category": operation_category,
        "target": {
            "kind": target_kind,
            "label": target_label,
            "redaction_status": "label_only",
        },
        "policy": {
            "decision": policy_decision,
            "reason": policy_reason,
        },
        "correlation": {
            "agent_session_id": session_id,
            "related_rule_ids": [],
        },
        "evidence": evidence,
    }


def annotate_runtime_artifact(
    path: Path,
    *,
    operation_label: str,
    site_label: str,
    exit_code: int,
    container_label: str = "job-search-runtime",
) -> Path:
    """Append host wrapper process/container labels to one runtime artifact."""

    operation_label = _safe_label(operation_label, "operation_label")
    site_label = _safe_label(site_label, "site_label")
    container_label = _safe_label(container_label, "container_label")
    payload = _load_payload(path)
    for event in payload["events"]:
        if (
            isinstance(event, dict)
            and event.get("event_type") == "process_exec"
            and event.get("operation") == operation_label
            and ((event.get("evidence") or {}).get("site_label") == site_label)
            and ((event.get("evidence") or {}).get("exit_code") == exit_code)
        ):
            return path

    policy_decision = "allow" if exit_code == 0 else "review"
    policy_reason = "approved cron wrapper operation" if exit_code == 0 else "cron wrapper nonzero exit"

    process_event = _base_event(
        payload,
        event_type="process_exec",
        actor_id="cron-wrapper",
        operation=operation_label,
        operation_category="process-exec",
        target_kind="command_label",
        target_label=operation_label,
        policy_decision=policy_decision,
        policy_reason=policy_reason,
        evidence={
            "site_label": site_label,
            "exit_code": exit_code,
            "arguments_stored": "label_only",
            "cwd_label": "job-search-skill-dir",
        },
        sequence_offset=1,
    )
    container_event = _base_event(
        payload,
        event_type="container_action",
        actor_id="cron-wrapper",
        operation=f"{operation_label}-container",
        operation_category="container-exec",
        target_kind="container_label",
        target_label=container_label,
        policy_decision=policy_decision,
        policy_reason=policy_reason,
        evidence={
            "site_label": site_label,
            "exit_code": exit_code,
            "container_id_stored": False,
            "remote_host_stored": False,
            "arguments_stored": "label_only",
        },
        sequence_offset=2,
    )

    payload["events"].extend([process_event, container_event])
    _atomic_write_json(path, payload)
    return path


def annotate_latest_and_archive(
    latest_path: Path,
    *,
    operation_label: str,
    site_label: str,
    exit_code: int,
    container_label: str = "job-search-runtime",
) -> list[Path]:
    """Annotate latest and its matching archive file when both exist."""

    payload = _load_payload(latest_path)
    archive_path = _archive_path_for_payload(latest_path, payload)
    paths = [archive_path, latest_path] if archive_path.exists() and archive_path != latest_path else [latest_path]
    annotated: list[Path] = []
    for path in paths:
        annotated.append(annotate_runtime_artifact(
            path,
            operation_label=operation_label,
            site_label=site_label,
            exit_code=exit_code,
            container_label=container_label,
        ))
    return annotated


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Annotate ClawGuard runtime-event artifacts with host wrapper labels.")
    parser.add_argument("--runtime-file", type=Path, default=DEFAULT_RUNTIME_FILE)
    parser.add_argument("--operation-label", required=True)
    parser.add_argument("--site-label", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--container-label", default="job-search-runtime")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = annotate_latest_and_archive(
            args.runtime_file,
            operation_label=args.operation_label,
            site_label=args.site_label,
            exit_code=args.exit_code,
            container_label=args.container_label,
        )
    except (OSError, json.JSONDecodeError, RuntimeEventAnnotationError) as exc:
        print(f"runtime-event annotation failed: {exc}", file=sys.stderr)
        return 1
    print("runtime-event annotation ok:")
    for path in paths:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
