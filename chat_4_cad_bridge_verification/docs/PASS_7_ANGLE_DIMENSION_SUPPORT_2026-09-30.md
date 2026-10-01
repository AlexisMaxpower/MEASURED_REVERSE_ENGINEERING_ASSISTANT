# Chat 4 — Pass 7 ANGLE Dimension Support

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-7`  
**Baseline:** Pass 6 `18ee968ee2472eab41fdefaa3935cdeb08b155a9`

## Scope

Pass 7 adds fail-closed vendor support for canonical verified `ANGLE` dimensions between exactly two `LINE` entities.

No shared canonical contract is changed.

## Vendor capability

Supported verified dimension combinations now include:

- `DISTANCE` in `mm`;
- `DIAMETER` in `mm`;
- `RADIUS` in `mm`;
- `ANGLE` in `deg`, exactly two LINE entities, value strictly between 0 and 180 degrees.

Unsupported ANGLE geometry or units are rejected before the worker process is invoked.

## SOLIDWORKS implementation

The C# worker selects the two line sketch segments and calls `IModelDoc2::AddDimension2` with deterministic text placement computed from the canonical line geometry. The placement selects the acute/obtuse sector whose size is closest to the requested canonical angle. The canonical degree value is then applied through the existing `SetSystemValue3` radian-conversion path.

Parallel or degenerate LINE pairs fail closed rather than guessing an angular dimension.

## API basis

SOLIDWORKS documentation states that angular dimensions can be created between two lines and that placement affects which angular sector is dimensioned. `IModelDoc2::AddDimension2` requires the target entities to be selected first and its text-position coordinates are specified in meters.

## Tests

`tests/test_solidworks_agent.py` adds boundary coverage for:

- ANGLE request accepted for two LINE entities in degrees;
- ANGLE unit mismatch rejected;
- ANGLE with a non-LINE entity rejected;
- zero/straight ANGLE values rejected.

Existing POINT/ARC, traceability and fail-closed boundary tests remain.

## Runtime truth

No controlled Windows 11 + installed SOLIDWORKS 2026 execution occurred in this pass.

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

GitHub-hosted CI cannot promote the real vendor runtime gate.

## Remaining vendor limitations

- canonical sketch constraints are not yet translated to SOLIDWORKS relations;
- solver conflict extraction remains follow-up work;
- real Windows/SOLIDWORKS compile + COM execution remains an environment gate.
