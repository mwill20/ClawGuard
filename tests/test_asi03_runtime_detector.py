import json
import unittest
from pathlib import Path

from detections.asi03_identity_abuse.detector import ASI03IdentityAbuseDetector


ROOT = Path(__file__).resolve().parents[1]
ASI03_POSITIVE = ROOT / "examples" / "runtime_events_asi03_positive.json"
NORMAL_OPS = ROOT / "examples" / "runtime_events_normal_ops.json"
CURATED_ASI03 = ROOT / "lessons" / "runtime-events" / "2026-05" / "digest-20260507T041020-50c7d030" / "runtime_events.json"
CURATED_FULL = ROOT / "lessons" / "runtime-events" / "2026-05" / "digest-20260507T174059-2121b8be" / "runtime_events.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ASI03RuntimeDetectorTests(unittest.TestCase):
    def test_positive_fixture_returns_identity_abuse_rules(self):
        findings = ASI03IdentityAbuseDetector().detect(_load(ASI03_POSITIVE))

        self.assertEqual(
            {finding.rule_id for finding in findings},
            {
                "ASI03_UNKNOWN_CREDENTIAL_LABEL",
                "ASI03_CREDENTIAL_EGRESS_MISMATCH",
            },
        )
        for finding in findings:
            self.assertEqual(finding.context["schema_version"], "runtime-events/0.1")
            self.assertEqual(finding.context["source_artifact"], "runtime-events")
            self.assertTrue(finding.event_ids)
            self.assertFalse(finding.evidence.get("raw_secret_stored", True))

    def test_clean_baselines_produce_zero_findings(self):
        detector = ASI03IdentityAbuseDetector()

        self.assertEqual(detector.detect(_load(NORMAL_OPS)), [])
        self.assertEqual(detector.detect(_load(CURATED_ASI03)), [])
        self.assertEqual(detector.detect(_load(CURATED_FULL)), [])

    def test_to_record_uses_session_and_avoids_job_id(self):
        finding = ASI03IdentityAbuseDetector().detect(_load(ASI03_POSITIVE))[0]

        record = finding.to_record()

        self.assertEqual(record["job_id"], "")
        self.assertEqual(record["agent_session_id"], "digest-20260507T180000-a5103001")
        self.assertIn("event_ids", json.loads(record["evidence"]))


if __name__ == "__main__":
    unittest.main()
