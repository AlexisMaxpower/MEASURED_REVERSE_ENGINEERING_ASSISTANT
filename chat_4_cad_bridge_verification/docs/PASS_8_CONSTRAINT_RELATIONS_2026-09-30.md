# Chat 4 — Pass 8 Verified Constraint Relations

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-8`  
**Baseline:** Pass 7 `d9633e3b8e95158d359e502e9797d4876384cd09`

## Scope

Pass 8 removes the blanket rejection of every non-empty canonical `constraints` array and adds a deliberately narrow fail-closed SOLIDWORKS relation subset.

No canonical/shared contract is changed.

## Supported real-worker constraints

Only canonical constraints with `status = VERIFIED` are eligible for real-worker transfer.

Supported combinations:

- `HORIZONTAL`: exactly one `LINE` -> `sgHORIZONTAL2D`;
- `VERTICAL`: exactly one `LINE` -> `sgVERTICAL2D`;
- `PARALLEL`: exactly two `LINE` entities -> `sgPARALLEL`;
- `PERPENDICULAR`: exactly two `LINE` entities -> `sgPERPENDICULAR`;
- `CONCENTRIC`: exactly two `CIRCLE`/`ARC` entities -> `sgCONCENTRIC`;
- `EQUAL`: exactly two `LINE` entities -> `sgSAMELENGTH`.

`COINCIDENT`, `TANGENT`, and `SYMMETRIC` remain explicitly unsupported in this pass. The current canonical contract identifies top-level entities but does not carry endpoint/sub-entity roles required to map every such relation without guessing.

`DETECTED`, `INFERRED`, and `UNRESOLVED` constraints are not silently promoted to authoritative SOLIDWORKS relations; they fail preflight.

## Python boundary

`src/mrea_cad_bridge/solidworks_agent.py` now:

- validates constraint status, type, entity arity and entity geometry before worker execution;
- rejects duplicate/unknown `entity_ids`;
- preserves validated canonical constraints in the slice-local `mrea.solidworks-agent.v1` request.

## C# worker

`ProtocolModels.cs` adds slice-local `ConstraintSpec`.

`SolidWorksTransfer.cs` applies constraints after deterministic entity creation and before dimensions.

For every relation the worker:

1. repeats the canonical compatibility validation;
2. selects the required sketch entities;
3. records `ISketchRelationManager::GetRelationsCount(swAll)`;
4. calls `IModelDoc2::SketchAddConstraints(...)` with the documented SOLIDWORKS relation identifier;
5. rebuilds the model;
6. requires relation count to increase;
7. checks `GetRelationsCount(swOverDefining)` and fails if the new relation over-defines the sketch.

This prevents a no-op API call or over-defining relation from being reported as successful constraint transfer.

## API basis

Official SOLIDWORKS API documentation documents `IModelDoc2::SketchAddConstraints` and relation identifiers including `sgHORIZONTAL2D`, `sgVERTICAL2D`, `sgPARALLEL`, `sgPERPENDICULAR`, `sgCONCENTRIC`, and `sgSAMELENGTH`. `ISketch::RelationManager` exposes `ISketchRelationManager`, whose `GetRelationsCount` supports `swAll` and `swOverDefining` filters.

## Boundary tests

`tests/test_solidworks_agent.py` now covers:

- preservation of all six supported verified relation types in the worker request;
- unsupported canonical constraint type rejected;
- non-VERIFIED constraint status rejected;
- incompatible constraint/entity geometry rejected;
- previous POINT/ARC, ANGLE, unit, unresolved, traceability and protocol tests remain.

## Runtime truth

No controlled Windows 11 + installed SOLIDWORKS 2026 execution occurred in this pass.

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
```

GitHub-hosted CI can validate Python/contracts/integration boundaries but cannot promote the vendor runtime gate.

## Remaining constraint limitations

- `COINCIDENT` endpoint/sub-entity semantics are not represented sufficiently by current `entity_ids` alone;
- `TANGENT` and `SYMMETRIC` remain fail-closed until a deterministic canonical-to-vendor mapping is defined;
- successful worker responses still expose an empty `constraint_conflicts` array; over-defining relations currently terminate the worker rather than mapping a solver conflict to a canonical dimension-level `CONSTRAINT_CONFLICT` item;
- real Windows/SOLIDWORKS compile + COM execution remains an environment gate.
