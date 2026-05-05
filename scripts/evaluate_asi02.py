#!/usr/bin/env python3
"""Evaluate ASI02 detector output against a labeled JSON fixture set."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detections.asi02_tool_misuse.detector import detect_tool_misuse  # noqa: E402


RULE_IDS = [
    "ASI02_EGRESS_REDIRECT",
    "ASI02_NOTIFY_REDIRECT",
    "ASI02_SHELL_INJECTION",
    "ASI02_FILE_PATH_REDIRECT",
]


def _score_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    per_rule = {
        rule_id: {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for rule_id in RULE_IDS
    }
    exact_matches = 0

    for record in records:
        expected = set(record.get("expected_rule_ids", []))
        predicted = {finding.rule_id for finding in detect_tool_misuse(record)}
        record["predicted_rule_ids"] = sorted(predicted)

        if predicted == expected:
            exact_matches += 1

        for rule_id in RULE_IDS:
            in_expected = rule_id in expected
            in_predicted = rule_id in predicted
            if in_expected and in_predicted:
                per_rule[rule_id]["tp"] += 1
            elif not in_expected and in_predicted:
                per_rule[rule_id]["fp"] += 1
            elif in_expected and not in_predicted:
                per_rule[rule_id]["fn"] += 1
            else:
                per_rule[rule_id]["tn"] += 1

    return {
        "records": records,
        "per_rule": per_rule,
        "exact_matches": exact_matches,
    }


def _metrics(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate(path: Path, include_timing: bool = True) -> dict[str, Any]:
    start = time.perf_counter()
    records = json.loads(path.read_text(encoding="utf-8"))
    scored = _score_counts(records)

    tp = sum(counts["tp"] for counts in scored["per_rule"].values())
    fp = sum(counts["fp"] for counts in scored["per_rule"].values())
    fn = sum(counts["fn"] for counts in scored["per_rule"].values())

    per_rule_metrics = {}
    for rule_id, counts in scored["per_rule"].items():
        per_rule_metrics[rule_id] = {
            **counts,
            **_metrics(counts["tp"], counts["fp"], counts["fn"]),
        }

    result = {
        "input_path": path.as_posix(),
        "record_count": len(records),
        "rule_ids": RULE_IDS,
        "exact_match_accuracy": round(scored["exact_matches"] / len(records), 4) if records else 0.0,
        "micro": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            **_metrics(tp, fp, fn),
        },
        "per_rule": per_rule_metrics,
        "records": [
            {
                "job_id": record.get("job_id", ""),
                "expected_rule_ids": sorted(record.get("expected_rule_ids", [])),
                "predicted_rule_ids": record.get("predicted_rule_ids", []),
            }
            for record in records
        ],
        "notes": [
            "Metrics are measured only on this small synthetic labeled fixture set.",
            "These results are not a real-world precision/recall benchmark.",
        ],
    }
    if include_timing:
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ASI02 detector against labeled fixtures.")
    parser.add_argument("--input", default="examples/asi02_labeled_eval.json")
    parser.add_argument("--output", default="")
    parser.add_argument("--expected-micro-f1", type=float, default=None)
    parser.add_argument("--hide-timing", action="store_true", help="Omit elapsed_ms for stable CI output.")
    args = parser.parse_args()

    result = evaluate(Path(args.input), include_timing=not args.hide_timing)
    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")

    if args.expected_micro_f1 is not None and result["micro"]["f1"] < args.expected_micro_f1:
        print(
            f"micro F1 {result['micro']['f1']} is below expected {args.expected_micro_f1}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
