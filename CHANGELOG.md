# Changelog

All notable changes to this project will be documented in this file.

The format follows a simple chronological log. This project does not currently publish versioned releases.

## Unreleased

### Added

- Repository readiness documentation set.
- Reviewer quickstart, usage examples, and sample input/output files.
- Security policy, contribution guide, evaluation notes, and limitations documentation.
- GitHub Actions CI for unit tests and synthetic ASI06 fixture evaluation.
- Synthetic ASI06 labeled fixture, evaluator script, and stable metrics artifact.
- Telemetry sample JSON and schema validator.
- Local preflight and cron-confirmation PowerShell helpers.
- ASI01 goal-hijack detector v1 under `detections/asi01_goal_hijack/detector.py`, wired into the runtime alongside ASI06 with corroborated-classification semantics.
- Source-status semantics in search audit/log output (`OK_NEW`, `ALL_KNOWN`, `EMPTY`, `ERROR`) and `already_known` and `newly_inserted_in_run` fields in digest summary so re-seen candidates are no longer indistinguishable from empty source results.
- Phase 2 plan documents under `docs/plans/` covering ASI02 module and telemetry export workflow.

### Current Phase

- Phase 1 complete: OpenClaw telemetry baseline, ASI06 detection module, ASI01 v1 detector, evidence-correlation tests, digest source-status clarity.
- Phase 2 begins: ASI02 detection module and curated telemetry export workflow.

## 2026-05-03

### Added

- ASI06 detector module under `detections/asi06_jd_content/detector.py`.
- Detector-backed OpenClaw runtime integration; inline ASI06 fallback removed after VPS cron confirmation.
- Lessons curriculum under `lessons/`.
- Post-compile telemetry hook and baseline telemetry documentation.

### Verified

- Local unit tests: `python -B -m unittest discover -s tests`.
- Current expected result: 15 tests passing.
- Synthetic ASI06 fixture result: 8 records, exact match 1.0, micro precision/recall/F1 1.0 on synthetic fixtures only.
- Telemetry sample schema validation: passing.
