# Limitations

## Known Limitations

- ASI06 detection is deterministic and rule-based.
- No semantic LLM review is implemented.
- ASI01 goal-hijack detection v1 is implemented, but it is deterministic and intentionally narrow.
- ASI02 tool-misuse detection is planned but not implemented.
- Precision, recall, and F1 are measured only on a small synthetic ASI06 fixture, not a real-world corpus.
- No larger real-world labeled evaluation corpus exists.
- The live deployment process is manual.
- Local fixture evaluator runtime is lightly measured; VPS cron runtime and memory performance are not yet measured.

## Failure Modes

| Failure Mode | Current Impact | Current Mitigation |
|---|---|---|
| `detections/` package missing during VPS deploy | Runtime import fails fast | Package `job_search_secure.py` and `detections/` together |
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
| Detector-backed ASI06/ASI01 runtime | Removes duplicate logic after confirmation | Requires packaged deploy of `job_search_secure.py` and `detections/` |
| Low-volume cron | Lower cost/noise | Slower data accumulation |

## Future Work

- Package `job_search_secure.py` and `detections/` as one deployment unit.
- Extend ASI01 with semantic review for ambiguous goal-redirect cases.
- Wire telemetry validation into exported VPS artifacts or hook post-checks.
- Add a larger real-world ASI06 evaluation fixture set.
- Add production cron runtime and memory telemetry.
- Add architecture diagram assets.
