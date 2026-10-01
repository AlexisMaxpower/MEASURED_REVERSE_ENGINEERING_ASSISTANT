# Build / Reuse Check — Chat 3 Pass 12 — Uncertainty-Aware Geometry Conflicts

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-12`  
**Baseline:** current shared `main` at `c888704b37e88b68c055f1095e6e9a4fc3650f7e`

## Problem

Chat 3 already preserves canonical physical measurement uncertainty through normalization and dimension binding, but the existing `GeometryConflictDetector` compares verified measurements against derived geometry with a fixed tolerance only.

That can report a geometry conflict even when the derived estimate remains inside explicitly supplied physical measurement uncertainty.

## Reuse decision

Reuse existing Chat-3-owned structures:

- `MeasurementRef.uncertainty`;
- `DimensionBinding.uncertainty`;
- `GeometryPipeline(conflict_detector=...)` injection point;
- `GeometryConflict.tolerance` as the effective tolerance actually used by the selected policy.

No new dependency, shared contract, canonical fixture, cross-chat API, or CAD-specific logic is required.

## Selected policy

For a verified dimension with a geometry estimate:

```text
effective_tolerance = baseline_tolerance + uncertainty_scale * measurement_uncertainty
```

Defaults:

```text
baseline_tolerance = 0.05
uncertainty_scale = 1.0
```

If uncertainty is absent, the uncertainty-aware detector behaves exactly like the existing fixed-tolerance policy.

Uncertainty never changes:

- measured value;
- unit;
- verified flag;
- provenance;
- geometry estimate;
- upstream confidence.

Invalid non-finite or negative uncertainty fails closed instead of being silently ignored.

## Compatibility decision

Do **not** silently change the default `GeometryConflictDetector` semantics in this pass.

Add `UncertaintyAwareGeometryConflictDetector` as an explicit policy that plugs into the existing `GeometryPipeline` injection point. This makes the capability usable immediately while preserving the established central default until orchestration explicitly adopts a policy change.

## Build decision

Implement locally in Chat 3 because this is MREA-specific evidence/truth policy. No third-party library is justified.

## Explicit non-goals

- no probabilistic distribution fitting;
- no unit conversion;
- no uncertainty inference or default fabrication;
- no constraint solver/entity movement;
- no shared schema change;
- no CAD-vendor behavior.
