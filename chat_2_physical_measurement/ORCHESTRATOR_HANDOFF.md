# ORCHESTRATOR HANDOFF — Chat 2

**Pass:** 5  
**Branch:** `chat-2/pass-5`  
**Baseline:** frozen Pass-4 head `f1472c244d4f7bee990ff65f77b580b3952d964a`  
**Executable implementation SHA:** `001959f1452fd8c3902f5af540cebe86e5e1afe0`  
**Implementation CI:** `MREA CI` run `36644904693` / run #315  
**Date:** 2026-09-30  
**From:** Chat 2 — Physical Measurement  
**To:** Chat 6 / integration review

> This handoff is the final worker commit for Pass 5. The branch is frozen after this file update. No post-handoff worker commit should be added unless integration review explicitly returns a fix request.

## Delivered functionality

Pass 5 makes Chat 2 uncertainty semantics unit-neutral.

Before this pass, uncertainty was stored internally as `uncertainty_mm`. After Pass 4 introduced correct `ANGLE -> deg` semantics, that field name became semantically wrong for angular measurements.

Pass 5 introduces primary field/API:

`uncertainty`

The uncertainty value is expressed in the same unit as `PhysicalMeasurement.unit`.

Examples:

- `42.18 mm ± 0.02 mm` -> `unit=mm`, `uncertainty=0.02`;
- `45.5 deg ± 0.5 deg` -> `unit=deg`, `uncertainty=0.5`.

## Backward compatibility

Legacy `uncertainty_mm` remains temporarily supported as a compatibility bridge for old callers, with fail-closed rules:

1. legacy `uncertainty_mm` is valid only for measurements whose resolved unit is `mm`;
2. if both `uncertainty` and `uncertainty_mm` are supplied, they must be numerically equal;
3. negative uncertainty values are rejected;
4. `ANGLE` plus legacy `uncertainty_mm` is rejected instead of silently treating millimetres as degrees;
5. old mm callers continue to observe mirrored `measurement.uncertainty_mm` while the new canonical internal value is `measurement.uncertainty`.

## Application flow

Updated `MeasurementSessionService`:

- `add_candidate()` accepts preferred `uncertainty` plus legacy `uncertainty_mm`;
- manual and reported candidate helpers propagate both consistently;
- unit selection still comes from `MeasurementTypeRegistry`.

Updated hands-free flow:

- `MeasurementCandidateContext` now carries primary unit-neutral `uncertainty`;
- the existing legacy mm field remains available for compatibility;
- voice/OCR/device candidates preserve uncertainty without changing explicit-confirmation rules.

## Canonical boundary

`CanonicalMeasurementAdapter` now serializes `measurement.uncertainty` directly.

No canonical contract change was required because canonical v1 already exposes the wire field as unit-neutral `uncertainty`.

Existing invariants remain unchanged:

- `ANGLE` uses `deg`;
- length-like types use `mm`;
- anchors remain raw `IMAGE_PX` in Chat 2;
- provenance/evidence/view/reference linkage is preserved;
- candidates remain unverified until explicit `USER_CONFIRMED`.

## Files changed in Pass 5

Modified:

- `src/physical_measurement/models.py`
- `src/physical_measurement/service.py`
- `src/physical_measurement/hands_free.py`
- `src/physical_measurement/boundary.py`
- `ORCHESTRATOR_HANDOFF.md`

Added:

- `tests/test_pass5_unit_neutral_uncertainty.py`
- `docs/PASS_5_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_5.md`

No file outside `chat_2_physical_measurement/` was modified.

## Build / Reuse

Recorded in `docs/PASS_5_BUILD_REUSE_CHECK.md`.

Decision: no third-party units library. This pass is a small MREA-internal model migration aligned with the existing canonical `uncertainty` field, not a unit-conversion problem.

## Tests added

`tests/test_pass5_unit_neutral_uncertainty.py` verifies:

1. angular uncertainty uses degrees and serializes canonically;
2. legacy `uncertainty_mm` remains compatible for mm measurements;
3. legacy mm uncertainty fails closed for angular measurements;
4. conflicting old/new uncertainty values fail closed;
5. hands-free context propagates unit-neutral angular uncertainty.

## GitHub Actions evidence

Executable implementation state:

```text
run_id = 36644904693
run_number = 315
head_sha = 001959f1452fd8c3902f5af540cebe86e5e1afe0
```

Required Chat-2 gates executed successfully:

- `Chat 2 / Measurement` — `success`;
- `Contracts / canonical fixtures` — `success`;
- `Integration / Chat 1 -> Chat 2` — `success`;
- `Integration / Chat 2 -> Chat 3` — `success`.

Conditional downstream jobs not selected for a Chat-2 worker push may remain skipped by repository CI policy and are not used as this acceptance gate.

## Known limitations / next debt

- the legacy `uncertainty_mm` compatibility field remains until all callers are migrated and a breaking cleanup is accepted;
- internal `PhysicalMeasurement` still owns exactly two anchors while canonical v1 permits one to three;
- angle-specific anchor geometry remains generic;
- snapping / automatic feature detection remains future work.

## Requested integration review

Verify:

1. unit-neutral uncertainty is the primary internal/API semantic;
2. mm legacy callers remain compatible;
3. angular legacy-mm input fails closed;
4. canonical wire output uses `uncertainty` with the measurement's own unit;
5. hands-free/manual/report candidate and explicit confirmation semantics did not regress;
6. required Chat-2 and adjacent boundary CI gates are green on implementation SHA `001959f1452fd8c3902f5af540cebe86e5e1afe0`;
7. worker ownership remains slice-local.

If accepted, integrate after Pass 4 according to orchestrator ordering. This branch is frozen after this handoff commit.
