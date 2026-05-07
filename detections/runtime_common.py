"""Shared runtime-event detection helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class RuntimeDetectionFinding:
    """Detector finding for runtime-event artifacts.

    Runtime findings are session/event oriented, not job oriented. The record
    shape intentionally mirrors the content detectors so evaluators and future
    persistence code can share conventions.
    """

    rule_id: str
    severity: str
    message: str
    event_ids: list[str]
    evidence: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)

    def to_record(self, agent_session_id: Optional[str] = None) -> dict[str, Any]:
        session_id = agent_session_id or str(self.context.get("agent_session_id", ""))
        return {
            "job_id": "",
            "agent_session_id": session_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": json.dumps({
                **self.evidence,
                "event_ids": self.event_ids,
            }, sort_keys=True),
            "context": json.dumps(self.context, sort_keys=True),
        }


def event_id(event: dict[str, Any]) -> str:
    return str(event.get("event_id", ""))


def event_label(event: dict[str, Any]) -> str:
    target = event.get("target") if isinstance(event.get("target"), dict) else {}
    return str(target.get("label", ""))


def policy_decision(event: dict[str, Any]) -> str:
    policy = event.get("policy") if isinstance(event.get("policy"), dict) else {}
    return str(policy.get("decision", ""))


def event_context(payload: dict[str, Any], detector_version: str) -> dict[str, Any]:
    return {
        "agent_session_id": str(payload.get("agent_session_id", "")),
        "schema_version": str(payload.get("schema_version", "")),
        "detector_version": detector_version,
        "source_artifact": "runtime-events",
    }
