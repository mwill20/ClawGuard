# Lessons

Teaching-oriented documentation built alongside the project. Each entry should be grounded in real OpenClaw or ClawGuard behavior, not invented examples.

## Current Artifacts

| Artifact | Status | Purpose |
|---|---|---|
| `clawguard-telemetry-baseline-001.md` | Complete | First clean OpenClaw telemetry baseline for ClawGuard Phase 1 |

## Planned Entries

| # | Title | Status |
|---|---|---|
| 1 | What Job Site Bot Detection Teaches Us About AI Agent Security Monitoring | Draft |
| 2 | Skill Supply Chain Security: Why We Write Our Own OpenClaw Skills | Draft |
| 3 | Zero Findings Are Still Telemetry | Candidate article from baseline 001 |

## Telemetry Artifacts

OpenClaw writes continuous ClawGuard telemetry on the VPS under:

```text
/data/clawguard/telemetry/
```

The post-compile hook writes:

```text
telemetry_<date>_<agent_session_id>.json
telemetry_<date>_<agent_session_id>.md
telemetry_latest.json
telemetry_latest.md
```

Curated samples can be pulled into `lessons/telemetry/` manually:

```powershell
.\scripts\export_latest_telemetry.ps1
```

Do not auto-push telemetry from the VPS. The current architecture decision is:

```text
VPS telemetry  = continuous operational record
Repo telemetry = curated artifacts only
Auto-push      = deferred intentionally
```

## Current Baseline

Baseline `digest-20260502T143953-c9eb7f4c` captured:

- 22 evaluated jobs.
- 0 ASI06 findings.
- 0 auto-prepared application packages.
- 0 Oxylabs credits used.
- LinkedIn and CyberSecJobs source coverage.
- USAJobs native API auth path verified with zero matches.

This is the clean-content baseline used to compare future sessions.

## Entry 1 Preview: Bot Detection And Agent Monitoring

Job platform anti-bot techniques map directly to AI agent security monitoring patterns:

| Job Site Technique | ClawGuard Equivalent |
|---|---|
| Speed detection | Agent behavioral velocity monitoring |
| Behavioral analysis | Agent action pattern analysis |
| Browser fingerprinting | Agent identity and provenance verification |
| Rate limiting | Agent rate anomaly detection |
| Human verification | Human-in-the-loop checkpoints |

## Entry 2 Preview: Skill Supply Chain Security

The OpenClaw skill ecosystem is powerful but expands the agent supply chain. ClawGuard's current policy is to write or audit every skill before deployment. That makes skill provenance a first-class security control.

## Entry 3 Preview: Zero Findings Are Still Telemetry

A clean ASI06 session is not a failure. It establishes:

- The detector can run without producing noise.
- The source mix can generate useful job telemetry without spending Oxylabs credits.
- The pipeline preserves correlation fields before the first live finding arrives.
- Future findings can be compared against a known clean baseline.
