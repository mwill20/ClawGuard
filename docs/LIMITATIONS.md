# Limitations

## Known Limitations

- ASI06 detection is deterministic and rule-based.
- No semantic LLM review is implemented.
- ASI01 goal-hijack detection is scaffolded but not runtime implemented.
- ASI02 tool-misuse detection is planned but not implemented.
- Precision, recall, and false-positive rate are not yet measured.
- No labeled evaluation corpus exists.
- The live deployment process is manual.
- Runtime and memory performance are not yet measured.

## Failure Modes

| Failure Mode | Current Impact | Current Mitigation |
|---|---|---|
| `detections/` package missing during VPS deploy | Runtime uses inline ASI06 fallback | Temporary fallback and runtime log signal |
| Provider returns duplicates | Digest may show 0 new jobs | Baseline docs distinguish duplicate results from pipeline failure |
| Provider returns 0 jobs | Digest may be empty | Source-level logs preserve provider behavior |
| Prompt injection phrased subtly | Regex may miss it | Future semantic review planned |
| Legitimate security job mentions prompt injection | Potential false positive if imperative wording matches | Evidence snippet supports human review |
| Telemetry file read during write | Possible partial read without atomic write | `os.replace()` atomic write implemented |

## Assumptions

- Local tests are run from the repository root.
- Runtime job data is untrusted.
- `.env` is kept outside Git.
- The OpenClaw deployment is controlled by the project owner.
- Human review remains required for real-world application actions.

## When Not to Use This Project

Do not use this project as:

- A production SIEM replacement.
- A complete agent security platform.
- A job application automation service.
- A benchmarked ML classifier.
- A tool for testing systems or accounts without permission.

## Trade-Offs

| Trade-Off | Benefit | Cost |
|---|---|---|
| Deterministic ASI06 rules | Simple, explainable, testable | Misses subtle semantic attacks |
| SQLite persistence | Easy local inspection | Limited scale/concurrency |
| Manual telemetry export | Avoids VPS auto-push risk | Requires operator discipline |
| Inline fallback | Safer manual deploy cutover | Temporary duplicate logic |
| Low-volume cron | Lower cost/noise | Slower data accumulation |

## Future Work

- Remove inline ASI06 fallback after normal cron confirmation.
- Add ASI01 runtime detector after live redirect evidence or ASI06 prompt-injection signal.
- Add telemetry schema validation.
- Add labeled ASI06 evaluation fixtures.
- Add lightweight CI.
- Add architecture diagram assets.
