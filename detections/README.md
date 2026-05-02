# ClawGuard Detections

Detection modules for OWASP Agentic Top 10 threats. Each detection targets a specific attack class with mapped telemetry signals.

## Phase 1 Targets

| Module | OWASP Code | Status |
|---|---|---|
| Goal Hijack Detection | ASI01 | Planned |
| Tool Misuse Detection | ASI02 | Planned |
| JD Content Detection | ASI06 | Scaffolded |

## Detection Architecture

Each detection module follows the 5-layer defense-in-depth pattern:

1. **Regex** - Fast pattern matching for known-bad indicators
2. **AST** - Structural analysis of agent actions
3. **ShellGuard** - Shell command classification and enforcement
4. **LLM** - Semantic analysis for novel/ambiguous threats
5. **SOC Ledger** - Logging, correlation, and human review

## Current Scaffold

- `asi06_jd_content/ASI06-001.md` documents the prompt-injection rule currently running inline in `job_search_secure.py`.
- `asi06_jd_content/README.md` defines the event schema, baseline, and extraction criteria.

ASI06 remains inline until enough live telemetry exists to extract the rules without guessing at the data shape.

## Development Guide

Detection modules will be built here as we map real telemetry from the OpenClaw deployment to OWASP threat patterns. See `target-agent/docs/attack-surface-recon.md` for current findings.
