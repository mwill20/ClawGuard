# Lessons

Teaching-oriented documentation built alongside the project. Each entry should be grounded in real OpenClaw or ClawGuard behavior, not invented examples.

## Current Artifacts

| Artifact | Status | Purpose |
|---|---|---|
| `00_Index.md` | Complete | Curriculum index for the current ClawGuard/OpenClaw Phase 1 implementation |
| `Lesson00_Project_Architecture.md` | Complete | Big-picture architecture and phase map |
| `Lesson01_OpenClaw_Runtime.md` | Complete | OpenClaw runtime and `job_search_secure.py` walkthrough |
| `Lesson02_ASI06_Detector.md` | Complete | ASI06 detector module deep dive |
| `Lesson03_SQLite_Telemetry_Ledger.md` | Complete | SQLite findings and evidence persistence |
| `Lesson04_Cron_And_Post_Compile_Telemetry.md` | Complete | VPS cron, post-compile hook, and telemetry latest files |
| `Lesson05_Testing_And_Defense_Lab.md` | Complete | Regression tests and ASI06 red-team lab |
| `Lesson06_ASI01_Goal_Hijack_Scaffold.md` | Complete | ASI01 detector v1 and semantic-first design decision |
| `Lesson07_Source_Compass_And_Phase2_Map.md` | Complete | Source-status semantics and Phase 2 planning map |
| `Lesson08_ASI02_Tool_Misuse_Defense_Lab.md` | Complete | ASI02 detector v1 and tool-misuse defense lab |
| `telemetry/2026-05/digest-20260505T163003-d9133ff9/` | Complete | First redacted curated Phase 2 clean-baseline telemetry set |
| `assets/asi06_red_team_jobs.json` | Complete | Local clean/adversarial sample jobs for lesson exercises |
| `clawguard-telemetry-baseline-001.md` | Complete | First clean OpenClaw telemetry baseline for ClawGuard Phase 1 |
| `clawguard-telemetry-baseline-002.md` | Complete | First autonomous full cron-chain telemetry baseline |
| `clawguard-telemetry-baseline-002-template.md` | Template | Capture the first autonomous full cron-chain telemetry run |

## Planned Entries

| # | Title | Status |
|---|---|---|
| 1 | What Job Site Bot Detection Teaches Us About AI Agent Security Monitoring | Draft |
| 2 | Skill Supply Chain Security: Why We Write Our Own OpenClaw Skills | Draft |
| 3 | Zero Findings Are Still Telemetry | Candidate article from baseline 001 |

## Curriculum Start

Start here:

```text
lessons/00_Index.md
```

The lesson sequence covers current implemented project phases:

```text
Architecture -> OpenClaw runtime -> ASI06 detector -> SQLite evidence -> cron telemetry -> tests/lab -> ASI01 detector -> source-status/Phase 2 map -> ASI02 defense lab
```

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

Curated samples can be pulled into `lessons/telemetry/` manually after redaction and schema validation:

```powershell
.\scripts\export_telemetry.ps1 -DryRun -Sessions digest-20260503T163003-b91b67e1
```

The first Phase 2 curated baseline is:

```text
lessons/telemetry/2026-05/digest-20260505T163003-d9133ff9/
```

Validate it with:

```powershell
python -B scripts\validate_telemetry.py --input lessons\telemetry\2026-05\digest-20260505T163003-d9133ff9\telemetry.json
```

To inspect the latest VPS telemetry without exporting files:

```powershell
.\scripts\check_latest_telemetry.ps1
```

Do not auto-push telemetry from the VPS. The current architecture decision is:

```text
VPS telemetry  = continuous operational record
Repo telemetry = curated artifacts only
Auto-push      = deferred intentionally
```

## Current Baselines

Baseline `digest-20260502T143953-c9eb7f4c` captured:

- 22 evaluated jobs.
- 0 ASI06 findings.
- 0 auto-prepared application packages.
- 0 Oxylabs credits used.
- LinkedIn and CyberSecJobs source coverage.
- USAJobs native API auth path verified with zero matches.

This is the clean-content baseline used to compare future sessions.

Baseline `digest-20260503T163003-b91b67e1` captured the first autonomous cron-chain run after telemetry hook deployment:

- Cron fired LinkedIn, CyberSecJobs, USAJobs, and compile.
- LinkedIn and CyberSecJobs returned already-known candidates.
- USAJobs returned 0 matches.
- Digest reported 0 newly inserted jobs.
- Post-compile telemetry hook completed.
- 0 findings, 0 auto-prepared packages, 0 credits used.

Baseline `digest-20260505T163003-d9133ff9` captured the first redacted curated Phase 2 telemetry export:

- Compile evaluated 0 jobs, so detector activation lines were not expected in that run.
- Post-compile telemetry hook completed.
- Export helper redacted, validated, and wrote JSON/Markdown artifacts under `lessons/telemetry/2026-05/`.
- 0 findings, 0 auto-prepared packages, 0 credits used.

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
- The ASI06 detector module can be tested independently of OpenClaw deployment timing.
- The source mix can generate useful job telemetry without spending Oxylabs credits.
- The pipeline preserves correlation fields before the first live finding arrives.
- Future findings can be compared against a known clean baseline.
