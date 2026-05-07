"""ClawGuard ASI05 unexpected code execution runtime detector."""

from __future__ import annotations

from typing import Any, Optional

from ..runtime_common import (
    RuntimeDetectionFinding,
    event_context,
    event_id,
    event_label,
    policy_decision,
)


DETECTOR_VERSION = "asi05-runtime-v1"

APPROVED_PROCESS_LABELS = {
    "python unittest discover",
    "evaluate asi06 fixture",
    "evaluate asi02 fixture",
    "evaluate combined detector fixture",
    "validate telemetry sample",
    "validate runtime events",
    "cron-wrapper-search-run",
    "cron-wrapper-compile-run",
}

APPROVED_CONTAINER_LABELS = {
    "openclaw-runtime",
    "job-search-runtime",
}

APPROVED_CONTAINER_OPERATIONS = {
    "docker_py_compile",
    "cron-wrapper-search-run-container",
    "cron-wrapper-compile-run-container",
}


class ASI05CodeExecutionDetector:
    """Detect unexpected execution or container actions from runtime events."""

    def __init__(
        self,
        approved_process_labels: Optional[set[str]] = None,
        approved_container_labels: Optional[set[str]] = None,
        approved_container_operations: Optional[set[str]] = None,
    ):
        self.approved_process_labels = approved_process_labels or APPROVED_PROCESS_LABELS
        self.approved_container_labels = approved_container_labels or APPROVED_CONTAINER_LABELS
        self.approved_container_operations = approved_container_operations or APPROVED_CONTAINER_OPERATIONS

    def detect(self, payload: dict[str, Any]) -> list[RuntimeDetectionFinding]:
        events = payload.get("events", [])
        if not isinstance(events, list):
            return []

        findings: list[RuntimeDetectionFinding] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") == "process_exec":
                finding = self._unapproved_process_label(payload, event)
            elif event.get("event_type") == "container_action":
                finding = self._unapproved_container_action(payload, event)
            else:
                finding = None
            if finding is not None:
                findings.append(finding)
        return findings

    def _unapproved_process_label(
        self,
        payload: dict[str, Any],
        event: dict[str, Any],
    ) -> Optional[RuntimeDetectionFinding]:
        label = event_label(event)
        operation = str(event.get("operation", ""))
        if label in self.approved_process_labels or operation in self.approved_process_labels:
            return None

        severity = "HIGH" if policy_decision(event) == "review" else "MEDIUM"
        return RuntimeDetectionFinding(
            rule_id="ASI05_UNAPPROVED_PROCESS_LABEL",
            severity=severity,
            message="Runtime process label is outside the approved command inventory.",
            event_ids=[event_id(event)],
            evidence={
                "process_label": label,
                "operation": operation,
                "approved_process_labels": sorted(self.approved_process_labels),
                "raw_command_stored": False,
                "arguments_stored": (event.get("evidence") or {}).get("arguments_stored", "unknown"),
            },
            context=event_context(payload, DETECTOR_VERSION),
        )

    def _unapproved_container_action(
        self,
        payload: dict[str, Any],
        event: dict[str, Any],
    ) -> Optional[RuntimeDetectionFinding]:
        label = event_label(event)
        operation = str(event.get("operation", ""))
        if label in self.approved_container_labels and operation in self.approved_container_operations:
            return None

        severity = "HIGH" if policy_decision(event) == "review" else "MEDIUM"
        evidence = event.get("evidence") if isinstance(event.get("evidence"), dict) else {}
        return RuntimeDetectionFinding(
            rule_id="ASI05_UNAPPROVED_CONTAINER_ACTION",
            severity=severity,
            message="Runtime container action is outside approved cron/deploy labels.",
            event_ids=[event_id(event)],
            evidence={
                "container_label": label,
                "operation": operation,
                "approved_container_labels": sorted(self.approved_container_labels),
                "approved_container_operations": sorted(self.approved_container_operations),
                "container_id_stored": bool(evidence.get("container_id_stored", False)),
                "remote_host_stored": bool(evidence.get("remote_host_stored", False)),
                "raw_command_stored": False,
            },
            context=event_context(payload, DETECTOR_VERSION),
        )


def detect_code_execution(payload: dict[str, Any]) -> list[RuntimeDetectionFinding]:
    return ASI05CodeExecutionDetector().detect(payload)
