# Chat 4 — Pass 6 POINT / ARC Vendor Support

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-6`  
**Baseline:** Pass 5 `b152539823b61b669b069301f3d7b687be429651`

## Scope

Pass 6 extends the SOLIDWORKS vendor worker geometry subset from `LINE/CIRCLE` to the complete mandatory canonical SketchPackage v1 subset:

- `POINT`
- `LINE`
- `CIRCLE`
- `ARC`

No shared canonical contract is changed.

## Python vendor boundary

`src/mrea_cad_bridge/solidworks_agent.py` now accepts all four canonical geometry entity types and preserves POINT/ARC fields in the slice-local JSON worker request.

Canonical constraints remain explicitly unsupported and fail closed. Verified dimension support remains `DISTANCE / DIAMETER / RADIUS`; ANGLE is still follow-up work.

## C# worker DTO

`solidworks_agent/ProtocolModels.cs` adds:

- `EntitySpec.point`;
- `EntitySpec.start_angle_deg`;
- `EntitySpec.end_angle_deg`.

These are slice-local vendor DTO fields, not shared contract changes.

## C# SOLIDWORKS transfer

`solidworks_agent/SolidWorksTransfer.cs` now validates and creates:

- POINT via `ISketchManager::CreatePoint`;
- ARC via `ISketchManager::CreateArc`.

Canonical coordinates/radius are converted from mm to SOLIDWORKS meters inside the vendor layer.

ARC endpoints are calculated from canonical center/radius/start/end angles. Direction is explicitly `+1`, matching the canonical/exporter convention of traversing start -> end counter-clockwise modulo 360 degrees.

A zero/full-circle ARC (start and end angles equivalent modulo 360) is rejected explicitly; canonical `CIRCLE` must be used instead.

## API basis

Implementation was checked against official SOLIDWORKS API documentation:

- `ISketchManager::CreatePoint` creates a point in the active sketch and accepts coordinates in model units used by the API;
- `ISketchManager::CreateArc` accepts center/start/end coordinates in meters and `Direction=+1` means counter-clockwise.

## Tests

`tests/test_solidworks_agent.py` now includes a boundary test proving POINT and ARC survive canonical mapping and vendor request generation with exact geometry values.

Existing fail-closed tests for unresolved geometry, canonical constraints, unsupported verified units, protocol mismatch, and worker errors remain.

## Runtime truth

No controlled Windows 11 + installed SOLIDWORKS 2026 execution occurred in this pass.

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

GitHub-hosted CI does not provide installed SOLIDWORKS and therefore cannot promote vendor runtime status to VERIFIED.

## Remaining vendor limitations

- ANGLE verified dimensions are not implemented in the real worker;
- canonical sketch constraints are not translated to SOLIDWORKS relations;
- solver conflict extraction remains follow-up work;
- real Windows/SOLIDWORKS compile + COM execution remains an environment gate.
