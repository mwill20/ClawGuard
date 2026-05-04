# Evaluation

## Evaluation Questions

1. Does the ASI06 detector identify known adversarial job-description patterns?
2. Does the detector avoid findings for clean sample input?
3. Does the OpenClaw runtime prefer the detector module when available?
4. Are findings queryable by `agent_session_id`?
5. Does post-compile telemetry preserve session-correlated results?

## Current Metrics

| Metric | Why It Matters | Result |
|---|---|---|
| Unit tests | Confirms detector, runtime, parser, evaluation, telemetry validation, profile privacy override, and DB behavior | 15/15 passing |
| Clean sample findings | Basic false-positive smoke check | 0 findings for `clean-example-001` |
| Adversarial sample findings | Basic true-positive smoke check | 4 ASI06 findings for `attack-example-001` |
| Synthetic labeled fixture exact match | Verifies expected rule sets on curated fixtures | 1.0 across 8 synthetic records |
| Synthetic labeled fixture micro precision/recall/F1 | Gives a reproducible detector smoke metric | 1.0 / 1.0 / 1.0 on synthetic fixtures only |
| Telemetry sample schema | Protects expected post-compile JSON shape | Passing for `examples/telemetry_sample.json` |
| Runtime performance | Useful for scaling expectations | Local fixture evaluator ran in about 3 ms for 8 synthetic records in one local run; VPS cron performance is not yet measured |

Important scope note: the labeled ASI06 fixture is small and synthetic. It is useful for regression and reviewer reproducibility, but it is not a real-world precision/recall benchmark.

## Test Procedure

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.0

OK
```

The exact runtime in seconds may vary.

## Sample Detector Procedure

```powershell
python -B -c "import json; from pathlib import Path; from detections.asi06_jd_content.detector import detect_job_content; jobs=json.loads(Path('examples/sample_input.json').read_text()); print(json.dumps([{'job_id': job['job_id'], 'rule_ids': [f.rule_id for f in detect_job_content(job)]} for job in jobs], indent=2))"
```

Expected output matches [examples/sample_output.json](../examples/sample_output.json).

## Labeled Fixture Evaluation

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

## Continuous Integration

GitHub Actions workflow: [.github/workflows/ci.yml](../.github/workflows/ci.yml)

The CI workflow runs:

```text
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests
python -B scripts/evaluate_asi06.py --input examples/asi06_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
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

Known baseline result:

- 0 ASI06 findings across clean sessions.
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
