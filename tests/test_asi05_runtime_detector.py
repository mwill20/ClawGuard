import json
import unittest
from pathlib import Path

from detections.asi05_code_execution.detector import ASI05CodeExecutionDetector


ROOT = Path(__file__).resolve().parents[1]
ASI05_POSITIVE = ROOT / "examples" / "runtime_events_asi05_positive.json"
NORMAL_OPS = ROOT / "examples" / "runtime_events_normal_ops.json"
CURATED_FULL = ROOT / "lessons" / "runtime-events" / "2026-05" / "digest-20260507T174059-2121b8be" / "runtime_events.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ASI05RuntimeDetectorTests(unittest.TestCase):
    def test_positive_fixture_returns_code_execution_rules(self):
        findings = ASI05CodeExecutionDetector().detect(_load(ASI05_POSITIVE))

        self.assertEqual(
            {finding.rule_id for finding in findings},
            {
                "ASI05_UNAPPROVED_PROCESS_LABEL",
                "ASI05_UNAPPROVED_CONTAINER_ACTION",
            },
        )
        for finding in findings:
            self.assertEqual(finding.severity, "HIGH")
            self.assertEqual(finding.context["schema_version"], "runtime-events/0.1")
            self.assertTrue(finding.event_ids)
            self.assertFalse(finding.evidence.get("raw_command_stored", True))

    def test_clean_baselines_produce_zero_findings(self):
        detector = ASI05CodeExecutionDetector()

        self.assertEqual(detector.detect(_load(NORMAL_OPS)), [])
        self.assertEqual(detector.detect(_load(CURATED_FULL)), [])

    def test_to_record_uses_session_and_avoids_job_id(self):
        finding = ASI05CodeExecutionDetector().detect(_load(ASI05_POSITIVE))[0]

        record = finding.to_record()

        self.assertEqual(record["job_id"], "")
        self.assertEqual(record["agent_session_id"], "digest-20260507T180500-a5105001")
        self.assertIn("event_ids", json.loads(record["evidence"]))


if __name__ == "__main__":
    unittest.main()
