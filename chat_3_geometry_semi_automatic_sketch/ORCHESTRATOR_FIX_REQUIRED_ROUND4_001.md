# ORCHESTRATOR FIX REQUIRED — Round 4 / Chat 3 / 001

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Target slice:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Directive:** `OD-2026-09-30-004`  
**Branch:** `chat-3/pass-8`  
**Previous frozen handoff:** `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`  
**Status:** `FIX_REQUIRED` — branch reopened only for this correction

## Evidence

Replacement Round-4 integration candidate:

`b5fdcd6324efd1396a3d57a28fc11e0dd0ba4afd`

Round-4 Truth CI:

`36752208521`

Failed job:

`Integration / Round 4 Chat 2 -> Chat 3 truth`

Failed test:

`test_round4_unit_neutral_uncertainty_is_preserved_through_geometry_binding`

Observed failure:

```text
MeasurementPackage contains uncertainty = 0.5
CanonicalInputAdapter returns MeasurementRef without uncertainty
AssertionError: silently dropping it is not Round-4 compliant
```

The same job proves that 1/2/3 anchor cardinality, `IMAGE_PX -> MAT_XY_MM` normalization and `mm` / `deg` unit handling already pass. Do not rewrite those working semantics.

## Defect

Chat 2 correctly emits canonical unit-neutral physical `uncertainty`.

Chat 3 currently consumes `measurement_id`, type, value, unit, verified/source and anchors but silently omits `uncertainty` when creating its internal measurement representation. The value therefore cannot survive into the measurement-to-dimension binding.

This violates Round-4 truth hardening: physical uncertainty must be preserved downstream or rejected explicitly; silent loss is forbidden.

## Required correction

Within Chat-3-owned code only:

1. extend the internal normalized measurement representation so optional canonical physical uncertainty is represented explicitly;
2. make `CanonicalInputAdapter` preserve the canonical numeric uncertainty value without unit conversion or reinterpretation;
3. propagate that uncertainty into the corresponding dimension binding produced by geometry;
4. preserve existing `mm` / `deg` units and existing 1/2/3 anchor semantics;
5. preserve existing fail-closed behavior for malformed/unsupported inputs;
6. do not infer missing uncertainty and do not manufacture a default precision value;
7. add deterministic Chat-3 slice tests for:
   - uncertainty present;
   - uncertainty absent;
   - at least one `deg`/3-anchor measurement;
   - existing `mm` behavior remains unchanged.

No change to `core/contracts/**` is authorized or currently required.

## Out of scope

Do not modify:

- Chat 1, 2, 4 or 5 code;
- root shared integration tests;
- `.github/workflows/**`;
- canonical contract/schema semantics;
- unrelated constraint/residual behavior that already passes the Round-4 Chat3->Chat4 gate.

## Acceptance gate

Before re-handoff:

- all Chat-3 slice tests must pass;
- existing Chat-3 functionality must remain green;
- update `ORCHESTRATOR_HANDOFF.md` with exact final branch SHA and test results;
- freeze the branch again after handoff.

Chat 6 will then replay the corrected Chat-3 owned tree into the official integration candidate and rerun:

`tests/integration/test_round4_chat2_to_chat3_truth.py`

and the full Round-4 Truth CI. Do not edit the shared gate merely to make it pass.
