# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` | Best effort |

This repository is a prototype / educational technical asset. It is not claimed to be production-hardened.

## Security Assumptions

- Job postings, search results, and scraped external content are untrusted.
- External content must be treated as data, not instruction.
- API keys and credentials are stored outside Git in `.env` or deployment secret stores.
- Local examples must not include real personal data, customer data, or private logs.
- Human approval is required for any real-world application submission.

## Threat Model Summary

| Asset | Threat | Current Control |
|---|---|---|
| OpenClaw job-search runtime | Prompt injection through job descriptions | ASI06 detector-backed checks with inline fallback |
| User personal information | Unsafe PII requests in job postings | `ASI06_PII_REQUEST` finding |
| Job scoring integrity | Keyword stuffing to inflate score | `ASI06_SKILL_STUFFING` finding and score penalty path |
| Application destination | Phishing or suspicious apply URLs | `ASI06_URL_MISMATCH` finding |
| Telemetry evidence | Lost or uncorrelated findings | `agent_session_id`, `job_id`, `context`, and `evidence` fields |
| Secrets | Accidental Git exposure | `.gitignore` excludes `.env`; `.env.example` uses placeholders |

## Agent Safety Boundaries

This agent workflow is allowed to:

- Search approved job sources in low-volume maintenance mode.
- Score and store job records.
- Record ASI06 findings for suspicious job content.
- Compile digest and telemetry summaries.

This workflow is not allowed to:

- Automatically submit job applications.
- Treat job posting text as agent instructions.
- Commit secrets, tokens, private logs, or real personal data.
- Claim production security coverage without measured evidence.

Human approval is required for:

- Any real application submission.
- Any deployment change that changes runtime behavior.
- Any use of real credentials or provider keys.

## Sensitive Data Handling

Do not commit:

- `.env`
- API keys
- email app passwords
- SSH keys
- real resumes with private contact data unless intentionally public
- private VPS logs
- customer or employer data

Use `.env.example` for safe placeholders only.

## Known Security Limitations

- ASI06 detection is deterministic and does not yet include semantic LLM review.
- ASI01 goal-hijack detection is scaffolded but not runtime implemented.
- Telemetry sample schema validation is implemented; exported VPS artifacts are not yet self-validated by the hook.
- The current VPS deployment flow is manual and should be treated as prototype operations.

## Reporting a Vulnerability

Open a GitHub issue for non-sensitive security concerns.

For sensitive reports, do not include secrets or exploit details in a public issue. TODO: Add a private security contact before external security review.
