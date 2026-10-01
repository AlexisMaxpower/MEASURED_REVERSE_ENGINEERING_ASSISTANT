# Chat 4 — Pass 14 Entity-Geometry Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-14`  
**Worker base:** shared `main@d6758d3a4c5eb2116ac2e48c3a77e65c10688b12`

## Purpose

Pass 13 moved verified-dimension shape validation into a fingerprinted Python/C# request envelope before SOLIDWORKS COM startup. The remaining geometry gap was that several vendor-specific entity validity checks still lived only in `SolidWorksTransfer.ValidateSlice(...)`, which runs after `SolidWorksSession.Open(request)`.

Pass 14 closes that specific gap without changing canonical contracts or shared CI.

## Slice-local entity capability contract

`src/mrea_cad_bridge/solidworks_entity_capabilities.py` defines:

```text
mrea.solidworks-entity-rules.v1
```

Declared fail-closed subset:

| Entity | Pre-COM vendor rule |
| --- | --- |
| `POINT` | `point.x/y` must exist and be finite |
| `LINE` | finite `start/end`; `length_squared_mm2 > 1e-24` |
| `CIRCLE` | finite center; finite radius `> 0` |
| `ARC` | finite center/radius/angles; radius `> 0`; positive-modulo angular span `>= 1e-12 deg` |

Entity IDs must also be non-empty and unique in one request. Unsupported types fail closed.

The Python evaluator returns machine-readable failure codes including `ENTITY_ID_INVALID`, `TYPE_UNSUPPORTED`, `POINT_INVALID`, `RADIUS_INVALID` and `GEOMETRY_DEGENERATE`.

## Worker fingerprint

The full worker capability projection now includes `geometry_entity_rules` alongside the existing geometry type list, dimension rules, constraints and protocol identity.

Pass-14 worker SHA-256:

```text
979a962f6a1a13d674abf0b6c9dcce16eae386e581a5c8597e89a4493b77a4d6
```

Any entity-rule change therefore requires an intentional matching C# worker update.

## Python preflight

`solidworks_agent._preflight(...)` now evaluates every entity before constraint or dimension preflight and before building the process request.

A degenerate line, invalid radius, zero/full-circle arc span, unsupported entity type or duplicate entity ID raises `CadAdapterError` before the worker subprocess is invoked.

## C# pre-COM envelope

`Program.ValidateRequestEnvelope(...)` now performs:

```text
ValidateEntityEnvelope(request)
ValidateDimensionEnvelope(request)
```

before `SolidWorksSession.Open(request)`.

`ValidateEntityEnvelope(...)` mirrors the fingerprinted POINT/LINE/CIRCLE/ARC rules. Request-invalid cases keep exit class `20`; they do not become COM-startup or CAD-transfer failures.

`SolidWorksTransfer.ValidateSlice(...)` remains as a deeper independent guard after session startup. Pass 14 does not remove downstream validation.

## Standing host qualification

This pass changes fingerprinted host-boundary files and adds `solidworks_entity_capabilities.py`. The file is added to `HOST_BOUNDARY_FILES` in `scripts/finalize_solidworks_qualification.py`.

Therefore an older successful `SOLIDWORKS_HOST_QUALIFICATION` manifest is reusable only if its fingerprint matches this new boundary. Software CI does not create or promote real-host qualification.

## Scope limit

Pass 14 is limited to deterministic request/entity compatibility before COM startup. It does not claim equivalence for SOLIDWORKS selection behavior, sketch solver behavior, relation creation, dimension creation, rebuild, native save or read-back behavior.

Canonical `mrea.contracts.v1` and canonical fixtures are unchanged.
