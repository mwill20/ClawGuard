# Evaluation

## Evaluation Questions

1. Does the ASI06 detector identify known adversarial job-description patterns?
2. Does the detector avoid findings for a clean sample input?
3. Does the OpenClaw runtime prefer the detector module when available?
4. Are findings queryable by `agent_session_id`?
5. Does post-compile telemetry preserve session-correlated results?

## Current Metrics

| Metric | Why It Matters | Result |
|---|---|---|
| Unit tests | Confirms detector, runtime, parser, and DB behavior | 11/11 passing |
| Clean sample findings | Basic false-positive smoke check | 0 findings for `clean-example-001` |
| Adversarial sample findings | Basic true-positive smoke check | 4 ASI06 findings for `attack-example-001` |
| Precision | Requires labeled corpus | Not yet measured |
| Recall | Requires labeled corpus | Not yet measured |
| Runtime performance | Useful for scaling expectations | Not yet measured |

## Test Procedure

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
python -B -m unittest discover -s tests
```

Expected output:

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.0

OK
```

## Sample Detector Procedure

```powershell
python -B -c "import json; from pathlib import Path; from detections.asi06_jd_content.detector import detect_job_content; jobs=json.loads(Path('examples/sample_input.json').read_text()); print(json.dumps([{'job_id': job['job_id'], 'rule_ids': [f.rule_id for f in detect_job_content(job)]} for job in jobs], indent=2))"
```

Expected output matches [examples/sample_output.json](../examples/sample_output.json).

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
| Missing `detections/` package in VPS single-file deploy | Inline ASI06 fallback | Remove fallback after cron confirmation and package deploy path |
| Ambiguous security job mentioning prompt injection defensively | Current regex may not trigger if wording is descriptive | Add semantic review for ambiguous cases |
| No labeled corpus | Metrics not measured | Build curated fixture set |
| Provider returns duplicate jobs | Digest may show 0 new jobs | Improve daily digest wording |

## Reproducibility Notes

- Local tests require no API keys.
- Sample input/output lives in `examples/`.
- Operational telemetry requires the deployed VPS environment and is not required for local evaluation.
