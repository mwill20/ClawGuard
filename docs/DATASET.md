# Dataset and Data Requirements

## Dataset Summary

This project does not require an external dataset for local tests.

It uses:

- User/runtime-provided job records from OpenClaw searches.
- Small synthetic sample records under `examples/` and `lessons/assets/` for local demonstration and lessons.
- A small synthetic labeled ASI06 fixture under `examples/` for reproducible detector smoke metrics.
- Curated telemetry baseline markdown files under `lessons/`.

## Local Sample Data

| File | Purpose | Records | License |
|---|---|---|---|
| `examples/sample_input.json` | Minimal clean/adversarial detector demo | 2 | Same as repository |
| `examples/sample_output.json` | Expected output for sample input | 2 | Same as repository |
| `examples/asi06_labeled_eval.json` | Synthetic labeled ASI06 evaluation fixture | 8 | Same as repository |
| `examples/asi06_labeled_eval_results.json` | Stable synthetic fixture evaluation result | 8 evaluated records | Same as repository |
| `examples/telemetry_sample.json` | Sample post-compile telemetry summary for schema validation | 1 telemetry summary | Same as repository |
| `lessons/assets/asi06_red_team_jobs.json` | Lesson defense lab | 2 | Same as repository |

## Runtime Data

Runtime job records are collected by OpenClaw from configured job sources. These records are not committed as a dataset in this repository.

Runtime records are stored on the deployed environment under the configured `CLAWGUARD_DATA_DIR`, typically:

```text
/data/clawguard/jobs.db
```

## Required Job Fields

The detector accepts dict-like or object-like job records. Recommended fields:

| Field | Description |
|---|---|
| `job_id` | Stable job identifier |
| `title` | Job title |
| `company` | Company or agency |
| `location` | Location string |
| `description` | Job description or snippet |
| `url` | Apply URL |
| `source` | Source platform, such as `linkedin` or `cybersecjobs` |

## Data Limitations

- A small synthetic labeled fixture exists for smoke metrics; no larger real-world labeled corpus exists yet.
- Runtime job source data may change daily.
- Search providers may return duplicates, incomplete descriptions, or zero matches.
- Sample data is synthetic and only validates smoke-test behavior; do not treat it as a representative benchmark.

## Bias and Representation Considerations

Not yet measured against a real-world corpus. Current source coverage is limited to a small maintenance set and should not be treated as representative of the broader cybersecurity job market.

## Quality Checks

Implemented:

- Unit tests for parser behavior.
- Unit tests for detector behavior.
- Sample input/output validation commands.
- Synthetic labeled ASI06 fixture evaluation with exact-match and micro precision/recall/F1 smoke metrics.
- Telemetry sample shape validation.

Recommended:

- Add larger real-world labeled false-positive and false-negative examples.
- Add provider-level data quality metrics.
- Add schema checks for job records before detector evaluation.
