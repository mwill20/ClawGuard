# Phase 4 Plans - Index

Last updated: 2026-05-07
Status: Draft handoff; Phase 3 final preflight passed, implementation can start after the next scheduled runtime-event check
Predecessor: Phase 3 runtime-event instrumentation, host redaction, and curated clean baselines

Phase 4 promotes runtime-event evidence into ASI03 and ASI05 detector work.
Phase 3 answered "can we observe runtime behavior safely?" Phase 4 answers
"which observed runtime behavior should become a finding?"

## Phase 4 Goals

1. Confirm scheduled runtime-event emission from the next daily cron run.
2. Build local-only ASI03 and ASI05 positive fixtures.
3. Add runtime-event detector modules that consume `runtime-events/0.1` payloads.
4. Prove curated clean baselines produce zero ASI03/ASI05 findings.
5. Add evaluator/preflight/CI coverage before any deployment.
6. Keep runtime findings observe-only until false-positive behavior is reviewed.

## Plan Documents

| Document | Scope |
|---|---|
| [PHASE4_SPEC.md](PHASE4_SPEC.md) | Phase 4 mission, tracks, gates, non-goals, and exit criteria |
| [PHASE4_DETECTOR_PROMOTION_SPEC.md](PHASE4_DETECTOR_PROMOTION_SPEC.md) | Concrete ASI03/ASI05 detector-promotion design from runtime events |
| `docs/plans/PHASE4_CHECKLIST.local.md` | Local tracking checklist; do not commit unless explicitly requested |

## Inputs from Phase 3

| Input | Purpose |
|---|---|
| `docs/plans/PHASE3_FALSE_POSITIVE_EXPECTATIONS.md` | Clean behavior contract future detectors must preserve |
| `examples/runtime_events_normal_ops.json` | Local clean false-positive fixture |
| `lessons/runtime-events/2026-05/digest-20260507T041020-50c7d030/` | Clean ASI03-ready provider baseline |
| `lessons/runtime-events/2026-05/digest-20260507T174059-2121b8be/` | Clean ASI03/ASI05-ready no-notify provider baseline |
| `scripts/validate_runtime_events.py` | Contract validator and readiness checks |

## Carry-Forward Watch Items

- The only Phase 2 items left are watch/curation tasks that depend on future
  real-world findings. Keep this note in forward checklists until a real
  finding-bearing or false-positive-worthy session exists, is redacted,
  validated, and curated.
- Scheduled runtime-event emission needs one more cron confirmation because the
  env flag was enabled after the May 7 scheduled run.
- Do not seed synthetic malicious jobs into live providers.

## Recommended Sequence

1. Re-run cron confirmation after the next scheduled compile and verify a
   scheduled runtime-event artifact exists.
2. Build ASI03/ASI05 positive fixtures locally under `examples/`.
3. Add detector modules with clean-baseline zero-finding tests.
4. Add evaluator scripts with exact-match/micro-F1 gates.
5. Wire preflight and CI.
6. Only then decide whether runtime findings should be persisted.

## Out of Scope Until Later

- Blocking/enforcement.
- Automated live-provider red-team injection.
- Runtime finding persistence before detector outputs stabilize.
- LLM-as-judge runtime finding promotion.
