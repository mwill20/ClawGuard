import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_runtime_events.py"
SAMPLE = ROOT / "examples" / "runtime_events_minimal.json"

spec = importlib.util.spec_from_file_location("validate_runtime_events", SCRIPT)
validate_runtime_events = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_runtime_events)


class RuntimeEventContractTests(unittest.TestCase):
    def test_sample_runtime_events_support_asi03_and_asi05_readiness(self):
        result = validate_runtime_events.load_and_validate(SAMPLE, require=["asi03", "asi05"])

        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["schema_version"], "runtime-events/0.1")
        self.assertEqual(result["event_count"], 7)
        self.assertEqual(result["event_type_counts"]["credential_use"], 1)
        self.assertEqual(result["event_type_counts"]["process_exec"], 1)

    def test_event_session_must_match_top_level_session(self):
        data = validate_runtime_events.json.loads(SAMPLE.read_text(encoding="utf-8"))
        data["events"][0]["agent_session_id"] = "digest-20260505T163003-deadbeef"

        with self.assertRaises(validate_runtime_events.RuntimeEventValidationError):
            validate_runtime_events.validate_runtime_events(copy.deepcopy(data))

    def test_raw_secret_fields_are_rejected(self):
        data = validate_runtime_events.json.loads(SAMPLE.read_text(encoding="utf-8"))
        data["events"][1]["evidence"]["token_value"] = "redacted-token-placeholder"

        with self.assertRaises(validate_runtime_events.RuntimeEventValidationError):
            validate_runtime_events.validate_runtime_events(copy.deepcopy(data))

    def test_asi03_readiness_requires_credential_use(self):
        data = validate_runtime_events.json.loads(SAMPLE.read_text(encoding="utf-8"))
        data["events"] = [
            event for event in data["events"]
            if event["event_type"] != "credential_use"
        ]

        with self.assertRaises(validate_runtime_events.RuntimeEventValidationError):
            validate_runtime_events.validate_runtime_events(copy.deepcopy(data), require=["asi03"])


if __name__ == "__main__":
    unittest.main()
