import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_combined_detectors.py"
FIXTURE = ROOT / "examples" / "combined_labeled_eval.json"

spec = importlib.util.spec_from_file_location("evaluate_combined_detectors", SCRIPT)
evaluate_combined_detectors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate_combined_detectors)


class CombinedEvaluationTests(unittest.TestCase):
    def test_combined_fixture_metrics_are_reproducible(self):
        result = evaluate_combined_detectors.evaluate(FIXTURE, include_timing=False)

        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["exact_match_accuracy"], 1.0)
        self.assertEqual(result["micro"]["precision"], 1.0)
        self.assertEqual(result["micro"]["recall"], 1.0)
        self.assertEqual(result["micro"]["f1"], 1.0)

        by_job = {
            record["job_id"]: record["predicted_rule_ids"]
            for record in result["records"]
        }
        self.assertEqual(by_job["combined-clean-001"], [])
        self.assertIn("ASI06_PROMPT_INJECTION", by_job["combined-goal-001"])
        self.assertIn("ASI01_EXTERNAL_GOAL_REDIRECT", by_job["combined-goal-001"])
        self.assertIn("ASI02_EGRESS_REDIRECT", by_job["combined-tool-001"])
        self.assertIn("ASI02_NOTIFY_REDIRECT", by_job["combined-full-001"])


if __name__ == "__main__":
    unittest.main()
