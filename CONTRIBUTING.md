# Contributing

Thank you for considering a contribution to ClawGuard.

This repository follows strict technical asset standards. New additions must help a reviewer understand, run, evaluate, and trust the project.

## Contribution Scope

Good contributions include:

- Detector rules with tests and evidence examples.
- Documentation that improves installation, usage, evaluation, security, or limitations.
- Reproducible examples under `examples/`.
- Lesson updates that explain real project behavior.
- Small fixes that make quickstart or tests more reliable.

Do not add:

- Secrets, API keys, private logs, personal data, or real customer data.
- Real resumes or real job-search profiles with private contact details.
- Unsupported production-readiness claims.
- Unmeasured metrics presented as results.
- Large generated artifacts unless they are intentionally required.

## New Addition Checklist

Before opening a pull request, check:

- [ ] README or docs are updated if behavior, setup, usage, or outputs changed.
- [ ] Tests are added or updated for code changes.
- [ ] Example input/output files are added for new user-facing behavior.
- [ ] Evaluation notes are updated if claims or metrics changed.
- [ ] ASI06 detector changes update `examples/asi06_labeled_eval.json` and rerun `scripts/evaluate_asi06.py` when rule behavior changes.
- [ ] Telemetry output changes update `examples/telemetry_sample.json` and rerun `scripts/validate_telemetry.py`.
- [ ] Security considerations are updated if trust boundaries or data handling changed.
- [ ] Limitations are updated if a new failure mode is discovered.
- [ ] No secrets or sensitive data are committed.
- [ ] Tracked resume/profile files remain fictional samples.
- [ ] `python -B -m unittest discover -s tests` passes locally.

## Documentation Standards

Every significant addition should answer:

```text
What changed?
Why does it matter?
How do I run it?
What input does it expect?
What output does it produce?
How is it tested?
What are the limitations?
```

Use `TODO:` or `Not yet measured` when facts are missing. Do not invent results.

## Development Setup

PowerShell:

```powershell
git clone https://github.com/mwill20/ClawGuard.git
Set-Location ClawGuard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests
```

## Pull Request Guidance

Keep changes small and reviewable. Prefer one logical topic per pull request.

For detector changes, include:

- Rule ID.
- Threat model.
- Evidence fields.
- False-positive notes.
- Tests.
- Sample input/output when useful.
- Labeled fixture updates when expected rule output changes.

Run the synthetic ASI06 fixture evaluation before submitting detector changes:

```powershell
python -B scripts\evaluate_asi06.py --input examples\asi06_labeled_eval.json --expected-micro-f1 1.0 --hide-timing
```

Run the telemetry validator before submitting telemetry hook changes:

```powershell
python -B scripts\validate_telemetry.py --input examples\telemetry_sample.json
```

## Security Issues

Do not open a public issue containing secrets or exploit details against a real third-party system. Follow [SECURITY.md](SECURITY.md).
