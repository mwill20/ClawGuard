# Phase 3 Plans - Index

Last updated: 2026-05-07
Status: In flight; Phase 2 gates closed, runtime hooks deployed, host-side redaction and first curated baseline complete

Phase 2 built the ASI02 detector, curated telemetry workflow, combined detector-chain lab, and the `runtime-events/0.1` contract. Phase 3 turns that contract into observed runtime telemetry before ASI03 and ASI05 are allowed to become runtime detectors.

## Phase 3 Goals

1. **Operational readiness check** - verify the May 6 daily schedule, email delivery, telemetry schema `1.2`, and ASI02 activation if a real compile evaluates jobs.

2. **Runtime event instrumentation** - emit structured `runtime-events/0.1` records from the OpenClaw runtime and host-side wrappers.

3. **Host-side redaction before automation** - redact runtime and telemetry artifacts on the VPS before any automated export path is considered.

4. **ASI03/ASI05 detector promotion gates** - keep ASI03 and ASI05 as review/spec work until structured runtime events and real review samples exist.

## Plan Documents

| Document | Scope |
|---|---|
| [PHASE3_TOMORROW_RUNBOOK.md](PHASE3_TOMORROW_RUNBOOK.md) | May 6, 2026 operational target: schedule, email, telemetry, ASI02 activation |
| [PHASE3_SPEC.md](PHASE3_SPEC.md) | Phase 3 umbrella spec: tracks, gates, acceptance criteria |
| [PHASE3_RUNTIME_INSTRUMENTATION_SPEC.md](PHASE3_RUNTIME_INSTRUMENTATION_SPEC.md) | Concrete implementation plan for `runtime-events/0.1` emission |
| `lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/` | First curated clean runtime-event baseline; host-redacted and locally validated |

## Recommended Sequence

1. Keep the May 6 operational evidence as the Phase 2 closeout record.
2. Keep Python-side runtime hooks for identity, provider credential/egress, and file-write events in observe-only mode.
3. Keep host-side redaction in front of every runtime-event export.
4. Decide whether to enable scheduled runtime-event emission after the curated clean baseline review.
5. Export only sanitized real review samples; do not seed live providers with synthetic malicious jobs.
6. Define ASI03/ASI05 false-positive expectations for normal cron/search/deploy behavior before writing detectors.
7. Revisit ASI03/ASI05 detector implementation only after runtime events exist, pass redaction/validation, and have reviewed false-positive expectations.

## Out of Scope Until Later

- ASI03/ASI05 runtime findings without structured runtime events.
- Automated repo pushes from the VPS.
- Synthetic attacker content in live job providers.
- Blocking/enforcement behavior before observe-only telemetry proves stable.
