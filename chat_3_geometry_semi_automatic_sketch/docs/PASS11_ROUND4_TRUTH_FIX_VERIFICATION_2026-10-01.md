# Chat 3 — Pass 11 — Round 4 truth-fix verification

**Role:** Geometry & Semi-Automatic Sketch  
**Branch:** `chat-3/pass-11`  
**Base:** corrected `chat-3/pass-8` re-handoff `d25ffae72df814cb26aaea5ae45f87a0e0f79400`  
**Current main observed before this pass:** `c034f7583d4e1f130f827d94a43762f3cad1a7e5`  
**Directive:** `OD-2026-09-30-004`  
**Pass type:** verification-only; no new runtime or shared-contract change

## Why this pass is verification-only

Current repository control state still says Chat 3 is reopened only for `ORCHESTRATOR_FIX_REQUIRED_ROUND4_001.md`. No new normal worker implementation is authorized. The selected Round-4 worker cut remains Pass 8; therefore Pass 11 does not add features, modify shared tests, alter canonical schemas, or touch another chat.

## Exact shared gate checked

Current `main` contains:

`tests/integration/test_round4_chat2_to_chat3_truth.py`

The blocker assertion chain is:

```text
MeasurementPackage uncertainty
-> CanonicalInputAdapter
-> MeasurementRef.uncertainty
-> GeometryPipeline / DimensionBinder
-> DimensionBinding.uncertainty
```

The shared test also verifies that `deg`, three anchors, and IMAGE_PX -> MAT_XY_MM normalization remain intact.

## Corrected Chat-3 implementation evidence

At corrected Pass-8 head `d25ffae72df814cb26aaea5ae45f87a0e0f79400`:

1. `MeasurementRef` has optional `uncertainty: float | None = None`.
2. `DimensionBinding` has optional `uncertainty: float | None = None` and serializes it explicitly.
3. `CanonicalInputAdapter` preserves canonical uncertainty without unit conversion using `_optional_uncertainty(...)`.
4. Missing uncertainty remains `None`; no default precision is manufactured.
5. Non-finite and negative uncertainty fail closed.
6. `DimensionBinder` copies `measurement.uncertainty` into `DimensionBinding.uncertainty` unchanged.

This matches the two uncertainty assertions in the current shared Round-4 Chat2 -> Chat3 truth gate.

## Worker CI evidence already produced by the corrected branch

GitHub Actions run on corrected worker implementation:

`36758766077`

Observed jobs:

```text
Chat 3 / Geometry                 SUCCESS
Contracts / canonical fixtures   SUCCESS
Chat 2 / Measurement             SUCCESS
Integration / Chat 2 -> Chat 3   SUCCESS
```

The Chat-3 slice run includes the deterministic `test_round4_uncertainty_preservation.py` regression suite; the preceding implementation run reported `74 passed in 0.49s`.

`Integration / Chat 3 -> Chat 4` remains a known stale-worker-ancestry shared-test failure and is not modified by this pass. Current main owns the corrected shared boundary implementation.

## Round-4 truth workflow boundary

`.github/workflows/round4_truth.yml` intentionally executes Round-4 boundary jobs only on the authorized central integration candidate / main review path. Chat 3 does not create or overwrite `integration/pass-4-candidate` and does not edit the workflow merely to self-certify.

Therefore central replay of corrected Chat-3-owned files remains an orchestrator action. This pass only records verifiable worker-side evidence.

## Pass 11 repository delta

Runtime code changed: **none**.  
Shared contracts changed: **none**.  
Shared integration tests changed: **none**.  
CI changed: **none**.  
Other chat-owned paths changed: **none**.  

Only this verification document is introduced by Pass 11.
