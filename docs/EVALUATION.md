# Evaluation

## Evaluation Questions

1. Does the ASI06 detector identify known adversarial job-description patterns?
2. Does the detector avoid findings for clean sample input?
3. Does ASI01 fire on corroborated goal-redirect content and stay silent on clean content?
4. Does ASI02 identify content-side tool-misuse attempts and stay silent on clean tool mentions?
5. Does the OpenClaw runtime require the detector modules when available?
6. Are findings queryable by `agent_session_id`?
7. Does post-compile telemetry preserve session-correlated results?

## Current Metrics

| Metric | Why It Matters | Result |
|---|---|---|
| Unit tests | Confirms ASI01/ASI02/ASI06 detectors, runtime, parser, evaluation, telemetry validation, runtime-event contract validation, runtime-event writer behavior, source-health digest reporting, review-session selection, export redaction, profile privacy override, and DB behavior | 69/69 passing |
| Clean sample findings | Basic false-positive smoke check | 0 findings for `clean-example-001` |
| Adversarial sample findings | Basic true-positive smoke check | 4 ASI06 findings for `attack-example-001` |
| ASI06 synthetic labeled fixture exact match | Verifies expected ASI06 rule sets on curated fixtures | 1.0 across 8 synthetic records |
| ASI06 synthetic labeled fixture micro precision/recall/F1 | Gives a reproducible ASI06 smoke metric | 1.0 / 1.0 / 1.0 on synthetic fixtures only |
| ASI02 synthetic labeled fixture exact match | Verifies expected ASI02 rule sets on curated fixtures | 1.0 across 7 synthetic records |
| ASI02 synthetic labeled fixture micro precision/recall/F1 | Gives a reproducible ASI02 smoke metric | 1.0 / 1.0 / 1.0 on synthetic fixtures only |
| Combined detector-chain synthetic fixture | Verifies ASI06, ASI01, and ASI02 run together through the runtime adapter | 1.0 exact match and micro F1 across 4 synthetic records |
| Telemetry sample schema | Protects expected post-compile JSON shape | Passing for `examples/telemetry_sample.json` |
| Runtime event contract | Defines ASI03/ASI05 prerequisite telemetry before runtime detectors exist | Passing for `examples/runtime_events_minimal.json` with `--require asi03 --require asi05` |
| Runtime performance | Useful for scaling expectations | Local fixture evaluator ran in about 3 ms for 8 synthetic records in one local run; VPS cron performance is not yet measured |

Important scope note: the labeled ASI06 and ASI02 fixtures are small and synthetic. They are useful for regression and reviewer reproducibility, but they are not real-world precision/recall benchmarks.

## Test Procedure

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
........................
----------------------------------------------------------------------
Ran 69 tests in 0.4

OK
```

The exact runtime in seconds may vary.

## Sample Detector Procedure

```powershell
python -B -c "import json; from pathlib import Path; from detections.asi06_jd_content.detector import detect_job_content; jobs=json.loads(Path('examples/sample_input.json').read_text()); print(json.dumps([{'job_id': job['job_id'], 'rule_ids': [f.rule_id for f in detect_job_content(job)]} for job in jobs], indent=2))"
```

Expected output matches [examples/sample_output.json](../examples/sample_output.json).

## ASI06 Labeled Fixture Evaluation

PowerShell:

```powershell
python -B scripts\evaluate_asi06.py --input examples\asi06_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Bash:

```bash
python -B scripts/evaluate_asi06.py --input examples/asi06_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Expected key results:

```text
"record_count": 8
"exact_match_accuracy": 1.0
"precision": 1.0
"recall": 1.0
"f1": 1.0
```

The stable checked-in result artifact is [examples/asi06_labeled_eval_results.json](../examples/asi06_labeled_eval_results.json).

## ASI02 Labeled Fixture Evaluation

PowerShell:

```powershell
python -B scripts\evaluate_asi02.py --input examples\asi02_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Bash:

```bash
python -B scripts/evaluate_asi02.py --input examples/asi02_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Expected key results:

```text
"record_count": 7
"exact_match_accuracy": 1.0
"precision": 1.0
"recall": 1.0
"f1": 1.0
```

The stable checked-in result artifact is [examples/asi02_labeled_eval_results.json](../examples/asi02_labeled_eval_results.json).

## Combined Detector-Chain Evaluation

This fixture runs the runtime detector chain instead of one detector module:

```text
job_search_secure.run_jd_security_detections()
  -> ASI06 content findings
  -> ASI01 goal-hijack findings
  -> ASI02 tool-misuse findings
```

PowerShell:

```powershell
python -B scripts\evaluate_combined_detectors.py --input examples\combined_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Bash:

```bash
python -B scripts/evaluate_combined_detectors.py --input examples/combined_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Expected key results:

```text
"record_count": 4
"exact_match_accuracy": 1.0
"precision": 1.0
"recall": 1.0
"f1": 1.0
```

The stable checked-in result artifact is [examples/combined_labeled_eval_results.json](../examples/combined_labeled_eval_results.json).

## Confusion-Matrix Workflow

The ASI06 and ASI02 evaluators emit per-rule confusion counts:

| Field | Meaning |
|---|---|
| `tp` | Rule expected and detector predicted it. |
| `fp` | Rule not expected but detector predicted it. |
| `fn` | Rule expected but detector missed it. |
| `tn` | Rule not expected and detector stayed silent. |

For ASI02, regenerate the checked-in result artifact with:

```powershell
python -B scripts\evaluate_asi02.py --input examples\asi02_labeled_eval.json --output examples\asi02_labeled_eval_results.json --expected-micro-f1 1.0 --hide-timing
```

Expected ASI02 matrix summary:

```text
ASI02_EGRESS_REDIRECT: tp=2 fp=0 fn=0 tn=5
ASI02_NOTIFY_REDIRECT: tp=2 fp=0 fn=0 tn=5
ASI02_SHELL_INJECTION: tp=2 fp=0 fn=0 tn=5
ASI02_FILE_PATH_REDIRECT: tp=2 fp=0 fn=0 tn=5
```

Use curated telemetry differently from synthetic fixtures:

- Synthetic fixtures are labeled, so they can produce TP/FP/FN/TN counts.
- Curated clean telemetry is operational evidence, so it is a false-positive smoke check unless manually labeled.
- Finding-bearing or false-positive curated samples should be added only when real telemetry warrants them.

## Continuous Integration

GitHub Actions workflow: [.github/workflows/ci.yml](../.github/workflows/ci.yml)

The CI workflow runs:

```text
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests
python -B scripts/evaluate_asi06.py --input examples/asi06_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
python -B scripts/evaluate_asi02.py --input examples/asi02_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
python -B scripts/validate_telemetry.py --input examples/telemetry_sample.json
```

## Telemetry Schema Validation

PowerShell:

```powershell
python -B scripts\validate_telemetry.py --input examples\telemetry_sample.json
```

Expected key result:

```text
"status": "valid"
```

The validator checks required top-level telemetry fields, `agent_session_id` format, digest summary keys, finding row shape, and count consistency between aggregate fields and `findings`.

## Live Baselines

Documented baselines:

- `lessons/clawguard-telemetry-baseline-001.md`
- `lessons/clawguard-telemetry-baseline-002.md`
- `lessons/telemetry/2026-05/digest-20260505T163003-d9133ff9/telemetry.json`

Known baseline result:

- 0 ASI06 and 0 ASI01 findings across clean sessions.
- ASI02 was implemented after the first two Markdown baselines; the curated Phase 2 JSON baseline records zero findings with schema `1.0`.
- 0 auto-prepared application packages.
- 0 Oxylabs credits used.

Zero findings are treated as clean-content telemetry, not as a failed detector.

## Known Failure Cases

| Failure Case | Current Handling | Future Improvement |
|---|---|---|
| Missing `detections/` package in deploy | Runtime import fails fast | Package `job_search_secure.py` and `detections/` together |
| Ambiguous security job mentioning prompt injection defensively | Synthetic fixture includes one clean defensive mention | Add larger real-world false-positive set and semantic review for ambiguous cases |
| Only a small synthetic labeled fixture exists | Metrics are scoped and caveated | Build larger curated real-world fixture set |
| Provider returns duplicate jobs | Digest may show 0 new jobs | Improve daily digest wording |

## Reproducibility Notes

- Local tests require no API keys.
- Sample input/output and the synthetic labeled fixture live in `examples/`.
- CI runs the same local tests and synthetic evaluation smoke command.
- Operational telemetry requires the deployed VPS environment and is not required for local evaluation.
