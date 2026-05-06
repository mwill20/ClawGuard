# Phase 3 Plans - Index

Last updated: 2026-05-05
Status: Draft handoff for May 6, 2026 execution

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

## Recommended Sequence

1. Run [PHASE3_TOMORROW_RUNBOOK.md](PHASE3_TOMORROW_RUNBOOK.md) after the May 6 9:30 AM PT compile.
2. If email and telemetry are healthy, begin runtime-event implementation.
3. Add local fixture coverage before emitting runtime events on the VPS.
4. Deploy runtime-event emission in observe-only mode.
5. Export only sanitized real review samples; do not seed live providers with synthetic malicious jobs.
6. Revisit ASI03/ASI05 detector implementation only after runtime events exist and pass redaction/validation.

## Out of Scope Until Later

- ASI03/ASI05 runtime findings without structured runtime events.
- Automated repo pushes from the VPS.
- Synthetic attacker content in live job providers.
- Blocking/enforcement behavior before observe-only telemetry proves stable.
