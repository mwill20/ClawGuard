#!/usr/bin/env python3
"""Evaluate ASI03/ASI05 runtime-event detectors on local fixtures."""

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

from detections.asi03_identity_abuse.detector import detect_identity_abuse
from detections.asi05_code_execution.detector import detect_code_execution
from scripts import validate_runtime_events


RULE_IDS = [
    "ASI03_UNKNOWN_CREDENTIAL_LABEL",
    "ASI03_CREDENTIAL_EGRESS_MISMATCH",
    "ASI05_UNAPPROVED_PROCESS_LABEL",
    "ASI05_UNAPPROVED_CONTAINER_ACTION",
]


def _metrics(tp: int, fp: int, fn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _expected_rule_ids(payload: dict[str, Any]) -> set[str]:
    expected = payload.get("expected_rule_ids", [])
    if not isinstance(expected, list):
        raise ValueError("expected_rule_ids must be a list when present")
    return {str(rule_id) for rule_id in expected}


def _predicted_rule_ids(payload: dict[str, Any]) -> set[str]:
    findings = [
        *detect_identity_abuse(payload),
        *detect_code_execution(payload),
    ]
    return {finding.rule_id for finding in findings}


def evaluate(path: Path, include_timing: bool = True) -> dict[str, Any]:
    start = time.perf_counter()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime detector fixture root must be an object")
    validate_runtime_events.validate_runtime_events(payload)

    expected = _expected_rule_ids(payload)
    predicted = _predicted_rule_ids(payload)
    per_rule: dict[str, dict[str, int]] = {}
    for rule_id in RULE_IDS:
        in_expected = rule_id in expected
        in_predicted = rule_id in predicted
        per_rule[rule_id] = {
            "tp": int(in_expected and in_predicted),
            "fp": int((not in_expected) and in_predicted),
            "fn": int(in_expected and (not in_predicted)),
            "tn": int((not in_expected) and (not in_predicted)),
        }

    tp = sum(counts["tp"] for counts in per_rule.values())
    fp = sum(counts["fp"] for counts in per_rule.values())
    fn = sum(counts["fn"] for counts in per_rule.values())

    per_rule_metrics = {
        rule_id: {
            **counts,
            **_metrics(counts["tp"], counts["fp"], counts["fn"]),
        }
        for rule_id, counts in per_rule.items()
    }

    result = {
        "agent_session_id": payload.get("agent_session_id", ""),
        "input_path": path.as_posix(),
        "rule_ids": RULE_IDS,
        "exact_match": predicted == expected,
        "expected_rule_ids": sorted(expected),
        "predicted_rule_ids": sorted(predicted),
        "micro": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            **_metrics(tp, fp, fn),
        },
        "per_rule": per_rule_metrics,
        "notes": [
            "Metrics cover local runtime-event fixtures only.",
            "These results are not a real-world precision/recall benchmark.",
        ],
    }
    if include_timing:
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ClawGuard runtime-event detector output.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--expected-micro-f1", type=float, default=None)
    parser.add_argument("--expect-no-findings", action="store_true")
    parser.add_argument("--hide-timing", action="store_true", help="Omit elapsed_ms for stable CI output.")
    args = parser.parse_args()

    try:
        result = evaluate(Path(args.input), include_timing=not args.hide_timing)
    except (OSError, json.JSONDecodeError, ValueError, validate_runtime_events.RuntimeEventValidationError) as exc:
        print(f"runtime detector evaluation failed: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")

    if args.expect_no_findings and result["predicted_rule_ids"]:
        print(f"expected no findings, got: {result['predicted_rule_ids']}", file=sys.stderr)
        return 1
    if args.expected_micro_f1 is not None and result["micro"]["f1"] < args.expected_micro_f1:
        print(
            f"micro F1 {result['micro']['f1']} is below expected {args.expected_micro_f1}",
            file=sys.stderr,
        )
        return 1
    if not result["exact_match"]:
        print("predicted runtime rule IDs did not exactly match fixture expectations", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
