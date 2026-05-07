"""ClawGuard ASI03 identity and privilege abuse runtime detector."""

from __future__ import annotations

from typing import Any, Optional

from ..runtime_common import (
    RuntimeDetectionFinding,
    event_context,
    event_id,
    event_label,
)


DETECTOR_VERSION = "asi03-runtime-v1"

APPROVED_CREDENTIAL_LABELS = {
    "brave-search-provider-credential",
    "usajobs-search-provider-credential",
}

APPROVED_EGRESS_DOMAINS = {
    "api.search.brave.com",
    "data.usajobs.gov",
}


class ASI03IdentityAbuseDetector:
    """Detect identity/credential misuse from runtime-event artifacts."""

    def __init__(
        self,
        approved_credential_labels: Optional[set[str]] = None,
        approved_egress_domains: Optional[set[str]] = None,
    ):
        self.approved_credential_labels = approved_credential_labels or APPROVED_CREDENTIAL_LABELS
        self.approved_egress_domains = approved_egress_domains or APPROVED_EGRESS_DOMAINS

    def detect(self, payload: dict[str, Any]) -> list[RuntimeDetectionFinding]:
        events = payload.get("events", [])
        if not isinstance(events, list):
            return []

        findings: list[RuntimeDetectionFinding] = []
        credential_events = [
            event for event in events
            if isinstance(event, dict) and event.get("event_type") == "credential_use"
        ]
        egress_events = [
            event for event in events
            if isinstance(event, dict) and event.get("event_type") == "network_egress"
        ]

        findings.extend(self._unknown_credential_findings(payload, credential_events))
        mismatch = self._credential_egress_mismatch(payload, credential_events, egress_events)
        if mismatch is not None:
            findings.append(mismatch)
        return findings

    def _unknown_credential_findings(
        self,
        payload: dict[str, Any],
        credential_events: list[dict[str, Any]],
    ) -> list[RuntimeDetectionFinding]:
        findings: list[RuntimeDetectionFinding] = []
        for event in credential_events:
            label = event_label(event)
            if not label or label in self.approved_credential_labels:
                continue
            findings.append(RuntimeDetectionFinding(
                rule_id="ASI03_UNKNOWN_CREDENTIAL_LABEL",
                severity="MEDIUM",
                message="Runtime used a credential label outside the approved provider inventory.",
                event_ids=[event_id(event)],
                evidence={
                    "credential_label": label,
                    "approved_credential_labels": sorted(self.approved_credential_labels),
                    "raw_secret_stored": False,
                },
                context=event_context(payload, DETECTOR_VERSION),
            ))
        return findings

    def _credential_egress_mismatch(
        self,
        payload: dict[str, Any],
        credential_events: list[dict[str, Any]],
        egress_events: list[dict[str, Any]],
    ) -> Optional[RuntimeDetectionFinding]:
        unknown_credentials = [
            event for event in credential_events
            if event_label(event) and event_label(event) not in self.approved_credential_labels
        ]
        external_egress = [
            event for event in egress_events
            if event_label(event) and event_label(event) not in self.approved_egress_domains
        ]
        if not unknown_credentials or not external_egress:
            return None

        credential = unknown_credentials[0]
        egress = external_egress[0]
        return RuntimeDetectionFinding(
            rule_id="ASI03_CREDENTIAL_EGRESS_MISMATCH",
            severity="HIGH",
            message="Runtime used an unapproved credential label in a session with non-approved network egress.",
            event_ids=[event_id(credential), event_id(egress)],
            evidence={
                "credential_label": event_label(credential),
                "destination_domain": event_label(egress),
                "approved_egress_domains": sorted(self.approved_egress_domains),
                "raw_secret_stored": False,
                "request_body_stored": False,
            },
            context=event_context(payload, DETECTOR_VERSION),
        )


def detect_identity_abuse(payload: dict[str, Any]) -> list[RuntimeDetectionFinding]:
    return ASI03IdentityAbuseDetector().detect(payload)
