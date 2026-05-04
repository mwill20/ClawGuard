import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_asi06.py"
FIXTURE = ROOT / "examples" / "asi06_labeled_eval.json"

spec = importlib.util.spec_from_file_location("evaluate_asi06", SCRIPT)
evaluate_asi06 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate_asi06)


class ASI06EvaluationTests(unittest.TestCase):
    def test_labeled_fixture_metrics_are_reproducible(self):
        result = evaluate_asi06.evaluate(FIXTURE, include_timing=False)

        self.assertEqual(result["record_count"], 8)
        self.assertEqual(result["exact_match_accuracy"], 1.0)
        self.assertEqual(result["micro"]["precision"], 1.0)
        self.assertEqual(result["micro"]["recall"], 1.0)
        self.assertEqual(result["micro"]["f1"], 1.0)
        self.assertTrue(
            all(
                record["expected_rule_ids"] == record["predicted_rule_ids"]
                for record in result["records"]
            )
        )


if __name__ == "__main__":
    unittest.main()
