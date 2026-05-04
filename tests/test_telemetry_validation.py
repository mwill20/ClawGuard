import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_telemetry.py"
SAMPLE = ROOT / "examples" / "telemetry_sample.json"

spec = importlib.util.spec_from_file_location("validate_telemetry", SCRIPT)
validate_telemetry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_telemetry)


class TelemetryValidationTests(unittest.TestCase):
    def test_sample_telemetry_matches_schema(self):
        result = validate_telemetry.load_and_validate(SAMPLE)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["agent_session_id"], "digest-20260503T163003-b91b67e1")
        self.assertEqual(result["finding_count"], 0)

    def test_finding_count_must_match_findings_length(self):
        data = {
            "generated_at": "2026-05-03T16:30:03.000000",
            "digest_path": "/data/clawguard/digests/digest_2026-05-03.json",
            "agent_session_id": "digest-20260503T163003-b91b67e1",
            "finding_count": 1,
            "rule_counts": {},
            "severity_counts": {},
            "finding_source_platform_counts": {},
            "digest_top_match_source_counts": {},
            "digest_summary": {
                "total_found": 0,
                "new_jobs": 0,
                "auto_prepared": 0,
                "credits_used_today": 0,
            },
            "findings": [],
        }

        with self.assertRaises(validate_telemetry.TelemetryValidationError):
            validate_telemetry.validate_telemetry(copy.deepcopy(data))


if __name__ == "__main__":
    unittest.main()
