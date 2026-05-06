#!/usr/bin/env python3
"""Observe-only runtime-event writer for ClawGuard Phase 3.

The writer is disabled unless CLAWGUARD_RUNTIME_EVENTS_ENABLED is truthy. When
enabled, callers start one session, record sanitized event dictionaries, and
flush one JSON document that matches the runtime-events/0.1 contract.
"""

from __future__ import annotations

import copy
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = "runtime-events/0.1"
DEFAULT_DATA_DIR = Path(os.getenv("CLAWGUARD_DATA_DIR", "/data/clawguard"))
DEFAULT_RUNTIME_EVENTS_DIR = DEFAULT_DATA_DIR / "runtime_events"
SESSION_ID_RE = re.compile(r"^digest-\d{8}T\d{6}-[0-9a-f]{8}$")
TRUTHY_VALUES = {"1", "true", "yes", "on"}

FORBIDDEN_KEYS = {
    "api_key",
    "absolute_path",
    "argv",
    "command_args",
    "command_line",
    "password",
    "profile_path",
    "raw_args",
    "raw_command",
    "raw_path",
    "raw_secret",
    "raw_token",
    "resume_path",
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
    re.compile(r"[A-Za-z]:\\(?:Users|Projects|docker|data|tmp)\\", re.IGNORECASE),
    re.compile(r"/(?:home|root|docker|data/clawguard|tmp)/"),
]


class RuntimeEventWriterError(ValueError):
    """Raised when runtime-event writer state or data is unsafe."""


@dataclass
class RuntimeEventSession:
    """In-memory singleton state for one observe-only runtime-event session."""

    agent_session_id: str
    output_dir: Path
    generated_at: str
    events: list[dict[str, Any]] = field(default_factory=list)
    event_sequence: int = 0
    self_write_recorded: bool = False
    flushed: bool = False
    archive_path: Optional[Path] = None


_SESSION: Optional[RuntimeEventSession] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in TRUTHY_VALUES


def runtime_events_enabled() -> bool:
    """Return whether runtime-event emission is enabled for this process."""

    return _env_truthy("CLAWGUARD_RUNTIME_EVENTS_ENABLED")


def _runtime_events_dir() -> Path:
    return Path(os.getenv("CLAWGUARD_RUNTIME_EVENTS_DIR", str(DEFAULT_RUNTIME_EVENTS_DIR)))


def _scan_for_sensitive_values(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lc = key.lower()
            if key_lc in FORBIDDEN_KEYS:
                raise RuntimeEventWriterError(f"{path}.{key} uses forbidden raw sensitive field name")
            _scan_for_sensitive_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_for_sensitive_values(item, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in FORBIDDEN_STRING_PATTERNS:
            if pattern.search(value):
                raise RuntimeEventWriterError(f"{path} appears to contain raw sensitive material")


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "event"


def _next_event_id(session: RuntimeEventSession, event_type: str, operation: str) -> str:
    session.event_sequence += 1
    slug = _sanitize_slug(operation or event_type)
    return f"evt-{session.agent_session_id}-{slug}-{session.event_sequence:03d}"


def _normalize_event(event: dict[str, Any], session: RuntimeEventSession) -> dict[str, Any]:
    normalized = copy.deepcopy(event)
    normalized.setdefault("event_id", _next_event_id(
        session,
        str(normalized.get("event_type", "event")),
        str(normalized.get("operation", "event")),
    ))
    normalized.setdefault("event_time", _utc_now())
    normalized.setdefault("agent_session_id", session.agent_session_id)

    correlation = normalized.setdefault("correlation", {})
    correlation.setdefault("agent_session_id", session.agent_session_id)
    correlation.setdefault("related_rule_ids", [])

    _scan_for_sensitive_values(normalized, "runtime_event")
    return normalized


def build_runtime_event(
    *,
    event_type: str,
    operation: str,
    operation_category: str,
    target_kind: str,
    target_label: str,
    actor_type: str = "agent",
    actor_id: str = "openclaw-job-search",
    source_component: str = "runtime_events.py",
    source_code_path: str = "target-agent/skills/job-search-custom/runtime_events.py",
    target_redaction_status: str = "label_only",
    policy_decision: str = "observe",
    policy_reason: str = "observe-only runtime event",
    evidence: Optional[dict[str, Any]] = None,
    related_rule_ids: Optional[list[str]] = None,
    event_id: Optional[str] = None,
    event_time: Optional[str] = None,
) -> dict[str, Any]:
    """Build a contract-shaped event without attaching session state."""

    event: dict[str, Any] = {
        "event_type": event_type,
        "actor": {
            "type": actor_type,
            "id": actor_id,
        },
        "source": {
            "component": source_component,
            "code_path": source_code_path,
        },
        "operation": operation,
        "operation_category": operation_category,
        "target": {
            "kind": target_kind,
            "label": target_label,
            "redaction_status": target_redaction_status,
        },
        "policy": {
            "decision": policy_decision,
            "reason": policy_reason,
        },
        "correlation": {
            "related_rule_ids": list(related_rule_ids or []),
        },
        "evidence": copy.deepcopy(evidence or {}),
    }
    if event_id is not None:
        event["event_id"] = event_id
    if event_time is not None:
        event["event_time"] = event_time
    return event


def start_runtime_event_session(
    agent_session_id: str,
    output_dir: Optional[Path] = None,
    generated_at: Optional[str] = None,
) -> Optional[RuntimeEventSession]:
    """Start the module-level runtime-event session if emission is enabled."""

    global _SESSION
    if not runtime_events_enabled():
        _SESSION = None
        return None
    if not SESSION_ID_RE.match(agent_session_id):
        raise RuntimeEventWriterError(f"invalid agent_session_id: {agent_session_id}")

    session = RuntimeEventSession(
        agent_session_id=agent_session_id,
        output_dir=Path(output_dir) if output_dir is not None else _runtime_events_dir(),
        generated_at=generated_at or _utc_now(),
    )
    _SESSION = session
    return session


def record_runtime_event(event: dict[str, Any]) -> bool:
    """Record a sanitized event into the active session.

    Returns False when runtime-event emission is disabled or no session has been
    started. This keeps Phase 3 observe-only instrumentation non-disruptive.
    """

    if _SESSION is None or not runtime_events_enabled():
        return False
    if _SESSION.flushed:
        raise RuntimeEventWriterError("cannot record runtime event after flush")

    _SESSION.events.append(_normalize_event(event, _SESSION))
    return True


def _runtime_event_write_event(session: RuntimeEventSession) -> dict[str, Any]:
    event = build_runtime_event(
        event_type="file_write",
        actor_type="agent",
        actor_id="openclaw-job-search",
        source_component="runtime_events.py",
        source_code_path="target-agent/skills/job-search-custom/runtime_events.py",
        operation="runtime_event_write",
        operation_category="file-write",
        target_kind="path_label",
        target_label="runtime-events",
        target_redaction_status="label_only",
        policy_decision="allow",
        policy_reason="approved runtime-event output path",
        evidence={
            "atomic_write": True,
            "raw_path_stored": False,
            "self_emission_guard": "direct_append_no_record_call",
        },
    )
    return _normalize_event(event, session)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp_path, path)


def flush_runtime_events() -> Optional[Path]:
    """Flush the active session to disk and return the archive path.

    The self `file_write` event is appended directly here rather than through
    record_runtime_event(), avoiding recursive file_write self-emission.
    """

    if _SESSION is None or not runtime_events_enabled():
        return None
    if _SESSION.flushed:
        return _SESSION.archive_path

    if not _SESSION.self_write_recorded:
        _SESSION.events.append(_runtime_event_write_event(_SESSION))
        _SESSION.self_write_recorded = True

    session_date = _SESSION.generated_at[:10]
    archive_path = _SESSION.output_dir / f"runtime_events_{session_date}_{_SESSION.agent_session_id}.json"
    latest_path = _SESSION.output_dir / "runtime_events_latest.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _SESSION.generated_at,
        "agent_session_id": _SESSION.agent_session_id,
        "events": _SESSION.events,
    }

    _scan_for_sensitive_values(payload, "runtime_events")
    _atomic_write_json(archive_path, payload)
    _atomic_write_json(latest_path, payload)
    _SESSION.archive_path = archive_path
    _SESSION.flushed = True
    return archive_path


def reset_for_tests() -> None:
    """Reset singleton writer state for deterministic unit tests."""

    global _SESSION
    _SESSION = None

