import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_asi02.py"
FIXTURE = ROOT / "examples" / "asi02_labeled_eval.json"

spec = importlib.util.spec_from_file_location("evaluate_asi02", SCRIPT)
evaluate_asi02 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate_asi02)


class ASI02EvaluationTests(unittest.TestCase):
    def test_fixture_evaluates_at_expected_micro_f1(self):
        result = evaluate_asi02.evaluate(FIXTURE, include_timing=False)

        self.assertEqual(result["record_count"], 7)
        self.assertEqual(result["micro"]["f1"], 1.0)
        self.assertEqual(result["exact_match_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
