# ORCHESTRATOR HANDOFF — Chat 3 — Pass 8 — Round 4 Fix 001

**From:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Owner directive:** `OD-2026-09-30-004`  
**Fix request:** `ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md`  
**Branch:** `chat-3/pass-8`  
**Reopened baseline:** `5457ab55d0139f40dd1bf24059e0a593156712c7`  
**Verified implementation head:** `7ca8f3b324f8ae206e733b92d8cb4328fee048c7`  
**Date:** 2026-09-30

## Status

`FIX_REQUIRED_001_IMPLEMENTED_AND_REFROZEN`

## Correction

Chat 3 now preserves canonical optional physical `uncertainty` through the complete owned boundary:

```text
MeasurementPackage.uncertainty
-> CanonicalInputAdapter
-> MeasurementRef.uncertainty
-> DimensionBinder
-> DimensionBinding.uncertainty
```

Semantics:

- finite non-negative numeric uncertainty is preserved exactly as a scalar;
- no unit conversion or reinterpretation is performed;
- absent/null uncertainty remains `None`;
- zero uncertainty remains `0.0`;
- malformed, non-finite or negative uncertainty fails closed;
- existing measurement value/unit, IMAGE_PX -> MAT_XY_MM normalization and 1/2/3-anchor behavior are unchanged.

## Changed Chat-3-owned implementation/test paths

- `src/mrea_geometry/models.py`
- `src/mrea_geometry/contracts.py`
- `src/mrea_geometry/core.py`
- `tests/test_round4_uncertainty_preservation.py`

No shared contract, root integration test, workflow, or other chat-owned runtime file was modified.

## Verification

GitHub Actions run for implementation head `7ca8f3b324f8ae206e733b92d8cb4328fee048c7`:

`36758554002`

Observed:

- `Chat 3 / Geometry`: **SUCCESS — 74 passed in 0.49s**;
- `Contracts / canonical fixtures`: **SUCCESS**;
- `Chat 2 / Measurement`: **SUCCESS**;
- `Integration / Chat 2 -> Chat 3`: **SUCCESS**;
- `Chat 4 / Generic CAD gate`: **SUCCESS**.

The old worker-ancestry `Integration / Chat 3 -> Chat 4` failure remains the pre-existing shared `cad_verification_report["dimensions"]` lookup. This fix does not touch that shared ancestry; current-main replay owns that reconciliation.

## Regression coverage added

- `mm` uncertainty present and preserved through binding;
- uncertainty absent remains absent/`None`;
- `deg` ANGLE with three anchors preserves uncertainty without conversion;
- zero uncertainty is preserved;
- non-finite, non-numeric and negative uncertainty fail closed.

## Freeze

This handoff refreezes `chat-3/pass-8` after the authorized Round-4 correction. No further normal worker changes are authorized without a new repository directive or explicit reopen request.
