# Chat 3 Pass 12 — Uncertainty-Aware Geometry Conflict Policy

**Date:** 2026-10-01  
**Branch:** `chat-3/pass-12`  
**Base:** `main` @ `c888704b37e88b68c055f1095e6e9a4fc3650f7e`

## Scope

Pass 12 implements the next Chat-3-owned uncertainty slice after Round 11 integrated physical uncertainty preservation.

## Added capability

New public policy:

`UncertaintyAwareGeometryConflictDetector`

It plugs into the existing `GeometryPipeline(conflict_detector=...)` boundary and computes:

```text
effective_tolerance = baseline_tolerance + uncertainty_scale * uncertainty
```

Only verified measurements with a derived geometry estimate participate in truth-conflict detection.

## Truth behavior

- measured values are never modified;
- measurement provenance is never changed;
- uncertainty is not inferred or strengthened;
- missing uncertainty preserves fixed-tolerance behavior;
- invalid negative/non-finite uncertainty fails closed;
- effective tolerance is written into `GeometryConflict.tolerance` when a conflict is emitted;
- unverified measurements are not promoted to truth conflicts.

## Compatibility

The existing default `GeometryConflictDetector` remains unchanged. Pass 12 adds an explicit policy rather than silently changing the central default.

## Tests

`tests/test_uncertainty_aware_conflicts.py` covers:

- legacy behavior when uncertainty is absent;
- suppression of a false conflict inside the uncertainty band;
- conflict visibility outside the effective band;
- deterministic `uncertainty_scale` behavior;
- unverified-measurement handling;
- fail-closed invalid uncertainty;
- fail-closed invalid detector configuration.

## Dependencies / ownership

New dependencies: none.  
Shared contracts changed: none.  
Shared integration tests changed: none.  
Other chat paths changed: none.  
CAD-vendor logic: none.

## Package

`mrea-chat3-geometry` version advances from `0.8.0` to `0.9.0`.
