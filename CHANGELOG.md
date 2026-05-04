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

### Current Phase

- ClawGuard Phase 1 is focused on OpenClaw telemetry, ASI06 detection, and evidence capture.
- ASI01 is scaffolded as documentation only.
- ASI02 is planned.

## 2026-05-03

### Added

- ASI06 detector module under `detections/asi06_jd_content/detector.py`.
- Detector-backed OpenClaw runtime integration with inline fallback.
- Lessons curriculum under `lessons/`.
- Post-compile telemetry hook and baseline telemetry documentation.

### Verified

- Local unit tests: `python -B -m unittest discover -s tests`.
- Current expected result: 15 tests passing.
- Synthetic ASI06 fixture result: 8 records, exact match 1.0, micro precision/recall/F1 1.0 on synthetic fixtures only.
- Telemetry sample schema validation: passing.
