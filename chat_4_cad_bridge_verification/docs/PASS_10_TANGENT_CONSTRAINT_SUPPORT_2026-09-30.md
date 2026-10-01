# Chat 4 — Pass 10 TANGENT Constraint Support

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-10`  
**Baseline:** Pass 9 `580203bd4c64c4382ffe60bd17cccccba4326580`

## Orchestration status

This is a user-authorized worker continuation after Pass 9. The central `main` directive is still `OD-2026-09-30-004`, which targeted and froze cumulative Pass 7. Therefore Pass 10 is **not** claimed as accepted by Chat 6 and does not modify the frozen `chat-4/pass-7` branch.

No canonical/shared contract, canonical fixture, Chat-6-owned workflow, or shared integration test is changed by this pass.

## Scope

Pass 10 implements a deliberately narrow fail-closed SOLIDWORKS vendor mapping for canonical verified `TANGENT` constraints.

Eligible canonical constraint:

- `type = TANGENT`;
- `status = VERIFIED`;
- exactly two entity IDs;
- each entity is `LINE`, `CIRCLE`, or `ARC`;
- at least one entity is curved (`CIRCLE` or `ARC`).

Explicitly rejected:

- `LINE / LINE`;
- any `POINT` participation;
- wrong arity;
- unknown or duplicate entity IDs;
- any status other than `VERIFIED`.

The restriction is intentional. `TANGENT` can be mapped at whole-sketch-entity level without inventing endpoint/sub-entity roles, unlike `COINCIDENT` and `SYMMETRIC`.

## Python vendor boundary

`src/mrea_cad_bridge/solidworks_agent.py` now:

- includes `TANGENT` in the supported vendor constraint subset;
- validates the two-entity arity;
- validates the `LINE/CIRCLE/ARC` geometry set;
- requires at least one `CIRCLE/ARC`;
- preserves the validated canonical constraint in the slice-local `mrea.solidworks-agent.v1` request;
- remains fail-closed for unsupported constraint combinations.

## SOLIDWORKS C# worker

`solidworks_agent/SolidWorksTransfer.cs` repeats the same compatibility checks before applying a relation.

The vendor relation mapping adds:

```text
TANGENT -> sgTANGENT
```

The existing relation safety path is reused unchanged:

1. select the two validated sketch entities;
2. record relation count;
3. call `IModelDoc2::SketchAddConstraints("sgTANGENT")`;
4. rebuild;
5. require relation count to increase;
6. fail if the sketch becomes over-defined.

A no-op API call or over-defining relation is therefore not reported as successful transfer.

## Capability manifest

`mrea.solidworks-capabilities.v1` is synchronized with worker behavior:

- `TANGENT` moved to the supported verified-constraint set;
- `COINCIDENT` and `SYMMETRIC` remain explicitly unsupported;
- the manifest records the same TANGENT geometry restriction;
- runtime/build status remains `UNVERIFIED`.

## Tests

Pass-10 tests cover:

- TANGENT included in supported verified constraint request preservation;
- LINE/CIRCLE TANGENT accepted by Python preflight;
- LINE/LINE TANGENT rejected;
- POINT participation rejected;
- capability manifest advertises TANGENT only after implementation;
- unsupported manifest set remains `COINCIDENT / SYMMETRIC`;
- non-VERIFIED TANGENT capability query remains false;
- caller mutation cannot alter the capability manifest singleton.

The repository CI result for the final Pass-10 HEAD is recorded separately and is the source of truth for executable generic/boundary gates.

## API basis

SOLIDWORKS API documentation for `IModelDoc2::SketchAddConstraints` lists `sgTANGENT` as a sketch relation identifier, and `IModelDoc2::SketchConstrainTangent` describes tangent creation for selected entities. This supports the vendor mapping choice but is not real-host execution evidence.

## Runtime truth

No controlled Windows 11 x64 + installed SOLIDWORKS 2026 x64 execution is performed by this pass.

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
NATIVE SLDPRT GENERATION/READBACK = UNVERIFIED
```

Static source inspection, Python tests and Linux GitHub Actions cannot promote those states.

## Remaining limitations

- `COINCIDENT` remains unsupported until endpoint/sub-entity role semantics are explicit enough to map without guessing;
- `SYMMETRIC` remains unsupported until symmetry-axis/sub-entity semantics are explicit;
- real SOLIDWORKS solver-conflict extraction is still not promoted into canonical constraint-conflict evidence;
- production C# compilation against installed SOLIDWORKS 2026 interop remains an external gate;
- native `.SLDPRT` creation/readback remains an external controlled-host gate;
- automated Windows/SOLIDWORKS CI is not established.
