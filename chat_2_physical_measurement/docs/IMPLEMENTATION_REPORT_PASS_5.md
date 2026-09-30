# Chat 2 — Pass 5 Implementation Report

## Baseline

Pass 5 is stacked on the frozen Pass-4 head:

`f1472c244d4f7bee990ff65f77b580b3952d964a`

The worker branch is:

`chat-2/pass-5`

## Problem closed

After Pass 4, `MeasurementType.ANGLE` correctly uses `unit = deg`, but Chat 2 still stored uncertainty internally as `uncertainty_mm`.

That created a semantic contradiction for angular measurements: the value itself was in degrees while the uncertainty field name still asserted millimetres.

## Implementation

`PhysicalMeasurement` now has primary unit-neutral field:

`uncertainty`

Its value is always expressed in the same unit as `measurement.unit`.

Examples:

- `42.18 mm ± 0.02 mm` → `unit=mm`, `uncertainty=0.02`;
- `45.5 deg ± 0.5 deg` → `unit=deg`, `uncertainty=0.5`.

### Backward compatibility

The legacy `uncertainty_mm` input remains temporarily supported for existing callers, but only when the measurement unit is `mm`.

Rules:

1. `uncertainty` is the preferred API;
2. `uncertainty_mm` is accepted only for mm measurements;
3. if both are supplied they must be numerically equal;
4. negative values fail closed;
5. angular measurements using `uncertainty_mm` fail closed rather than silently treating millimetres as degrees.

For a legacy mm measurement, the model resolves the value into `uncertainty` and keeps `uncertainty_mm` mirrored for compatibility.

For non-mm measurements, `uncertainty_mm` remains `None`.

## Application flow

Updated `MeasurementSessionService`:

- `add_candidate()` accepts primary `uncertainty` plus legacy `uncertainty_mm`;
- `add_manual_candidate()` and `add_reported_candidate()` propagate both consistently.

Updated `MeasurementCandidateContext` and `HandsFreeMeasurementController`:

- hands-free voice/OCR/device flows can now carry unit-neutral uncertainty;
- existing legacy mm context remains accepted.

## Canonical boundary

Updated `CanonicalMeasurementAdapter` to serialize:

`measurement.uncertainty`

instead of reading `measurement.uncertainty_mm`.

No canonical schema change was required because canonical v1 already names the wire field simply `uncertainty`.

## Tests

Added `tests/test_pass5_unit_neutral_uncertainty.py` covering:

1. angle uncertainty is stored in degrees and serialized canonically;
2. legacy `uncertainty_mm` remains compatible for mm measurements;
3. legacy `uncertainty_mm` fails closed for angle measurements;
4. conflicting `uncertainty` and `uncertainty_mm` values fail closed;
5. hands-free context propagates unit-neutral angular uncertainty.

Existing Phase A/Pass 2/Pass 3/Pass 4 tests remain part of the Chat-2 CI suite.

## Ownership

Only `chat_2_physical_measurement/` is modified.

No canonical contract, shared fixture, CI workflow, Chat 1/3/4/5 implementation, or shared integration test is changed.

## Remaining debt

- legacy `uncertainty_mm` can be removed only after all callers are migrated and an explicit breaking cleanup is accepted;
- internal model still uses exactly two anchors;
- angle-specific anchor geometry remains generic;
- snapping / automatic feature detection is still future work.
