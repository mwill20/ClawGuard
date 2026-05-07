import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import validate_runtime_events


ROOT = Path(__file__).resolve().parents[1]
ANNOTATOR_PATH = (
    ROOT / "target-agent" / "skills" / "job-search-custom" / "clawguard_annotate_runtime_events.py"
)
NORMAL_OPS = ROOT / "examples" / "runtime_events_normal_ops.json"
annotator_spec = importlib.util.spec_from_file_location("clawguard_annotate_runtime_events", ANNOTATOR_PATH)
runtime_event_annotator = importlib.util.module_from_spec(annotator_spec)
sys.modules[annotator_spec.name] = runtime_event_annotator
annotator_spec.loader.exec_module(runtime_event_annotator)


class RuntimeEventHostAnnotationTests(unittest.TestCase):
    def test_annotator_appends_label_only_process_and_container_events(self):
        payload = json.loads(NORMAL_OPS.read_text(encoding="utf-8"))
        payload["events"] = [
            event for event in payload["events"]
            if event["event_type"] not in {"process_exec", "container_action", "policy_decision"}
        ]

        with tempfile.TemporaryDirectory() as temp:
            runtime_path = Path(temp) / "runtime_events_latest.json"
            runtime_path.write_text(json.dumps(payload), encoding="utf-8")

            runtime_event_annotator.annotate_runtime_artifact(
                runtime_path,
                operation_label="cron-wrapper-search-run",
                site_label="usajobs",
                exit_code=0,
                container_label="job-search-runtime",
            )

            annotated = json.loads(runtime_path.read_text(encoding="utf-8"))
            result = validate_runtime_events.validate_runtime_events(
                copy.deepcopy(annotated),
                require=["asi03", "asi05"],
            )
            event_types = [event["event_type"] for event in annotated["events"]]

        self.assertEqual(result["status"], "valid")
        self.assertIn("process_exec", event_types)
        self.assertIn("container_action", event_types)
        self.assertNotIn("raw_command", json.dumps(annotated))
        self.assertNotIn("openclaw-utxu", json.dumps(annotated))

    def test_annotator_rejects_raw_command_shaped_label(self):
        payload = json.loads(NORMAL_OPS.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp:
            runtime_path = Path(temp) / "runtime_events_latest.json"
            runtime_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(runtime_event_annotator.RuntimeEventAnnotationError):
                runtime_event_annotator.annotate_runtime_artifact(
                    runtime_path,
                    operation_label="python job_search_secure.py --site usajobs",
                    site_label="usajobs",
                    exit_code=0,
                )


if __name__ == "__main__":
    unittest.main()
