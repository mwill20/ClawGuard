# Dataset and Data Requirements

## Dataset Summary

This project does not require an external dataset for local tests.

It uses:

- User/runtime-provided job records from OpenClaw searches.
- Small synthetic sample records under `examples/` and `lessons/assets/` for local demonstration and lessons.
- Curated telemetry baseline markdown files under `lessons/`.

## Local Sample Data

| File | Purpose | Records | License |
|---|---|---|---|
| `examples/sample_input.json` | Minimal clean/adversarial detector demo | 2 | Same as repository |
| `examples/sample_output.json` | Expected output for sample input | 2 | Same as repository |
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

- No labeled evaluation corpus exists yet.
- Runtime job source data may change daily.
- Search providers may return duplicates, incomplete descriptions, or zero matches.
- Sample data is synthetic and only validates smoke-test behavior.

## Bias and Representation Considerations

Not yet measured. Current source coverage is limited to a small maintenance set and should not be treated as representative of the broader cybersecurity job market.

## Quality Checks

Implemented:

- Unit tests for parser behavior.
- Unit tests for detector behavior.
- Sample input/output validation commands.

Recommended:

- Add labeled false-positive and false-negative examples.
- Add provider-level data quality metrics.
- Add schema checks for job records before detector evaluation.
