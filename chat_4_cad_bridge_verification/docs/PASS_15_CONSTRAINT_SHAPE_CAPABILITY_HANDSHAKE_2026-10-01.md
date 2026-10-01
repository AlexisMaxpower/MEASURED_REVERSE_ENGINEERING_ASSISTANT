# Chat 4 — Pass 15 Constraint-Shape Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-15`  
**Worker base:** shared `main@99d8c6d9322f3669a43226e4fd2675fe683ab9f6`

## Purpose

Pass 13 moved verified-dimension shape validation into the fingerprinted Python/C# request envelope before SOLIDWORKS COM startup. Pass 14 did the same for entity geometry. The remaining deterministic request-shape gap was canonical constraints: Python preflight already validated the supported constraint/entity combinations, but the C# request envelope deferred those checks until `SolidWorksTransfer.ValidateSlice(...)`, after `SolidWorksSession.Open(request)`.

Pass 15 closes that gap without changing canonical MREA contracts or shared CI.

## Machine-readable constraint rules

`build_solidworks_capabilities_v1()["constraints"]["rules"]` now declares the exact fail-closed subset used by Python and mirrored by C#:

- non-empty `constraint_id` required;
- entity IDs must be distinct;
- referenced entities must exist;
- status must be `VERIFIED`;
- `HORIZONTAL` / `VERTICAL`: exactly one `LINE`;
- `PARALLEL` / `PERPENDICULAR` / `EQUAL`: exactly two `LINE` entities;
- `CONCENTRIC`: exactly two `CIRCLE`/`ARC` entities;
- `TANGENT`: exactly two `LINE`/`CIRCLE`/`ARC` entities with at least one `CIRCLE`/`ARC`.

The Python evaluator now consumes those declared entity-type patterns directly instead of maintaining a separate hard-coded decision tree.

## Fingerprints

The narrower constraint fingerprint now covers the exact machine-readable rule object because `solidworks_constraint_handshake.py` fingerprints the complete `constraints` capability object.

Pass-15 constraint SHA-256:

```text
5eac12828b4255e05b17732093bf881e24a64c016abe5828573e4235be665ae4
```

The full worker capability projection already includes the complete `constraints` object, so the same rule expansion also changes the worker fingerprint.

Pass-15 worker SHA-256:

```text
0e1c5ca75945f7a62ac6cbd126a6523bc3b851e1ec051345fc265f89b8c3172f
```

Both hashes are embedded in `Program.cs` and checked before COM startup.

## C# pre-COM envelope

`Program.ValidateRequestEnvelope(...)` now executes in this order:

```text
ValidateEntityEnvelope(request)
ValidateConstraintEnvelope(request)
ValidateDimensionEnvelope(request)
```

`ValidateConstraintEnvelope(...)` rejects invalid IDs, duplicate IDs, non-VERIFIED status, unsupported types, duplicate/unknown entity references, unsupported arity and unsupported entity-type combinations before `SolidWorksSession.Open(request)`.

These failures remain request-invalid (`exit 20`) rather than being misclassified as COM-startup or CAD-transfer failures.

`SolidWorksTransfer.ValidateSlice(...)` remains an independent downstream guard after session startup.

## Tests

Pass 15 updates constraint capability and handshake tests to prove:

- the rule object is explicit and caller-safe;
- the evaluator rejects missing constraint IDs;
- exact supported entity-type patterns remain fail closed;
- Python and C# embed the same constraint fingerprint;
- the full worker fingerprint changes with the constraint rules;
- C# constraint-envelope validation occurs after entity-envelope validation and before dimension-envelope validation;
- the complete request envelope still executes before `SolidWorksSession.Open(request)`.

## Standing host qualification

This pass changes fingerprinted host-boundary files already present in `HOST_BOUNDARY_FILES` (`solidworks_capabilities.py` and `Program.cs`). Therefore any older positive `SOLIDWORKS_HOST_QUALIFICATION` is reusable only if its recorded host-boundary fingerprint matches this changed boundary and the controlled host has not materially changed.

Software-only CI does not create or promote real-host qualification.

## Scope limit

Pass 15 hardens deterministic request/constraint compatibility only. It does not claim SOLIDWORKS solver equivalence, relation-creation success, over-definition behavior, selection semantics, rebuild behavior, native save behavior, or read-back behavior.

Canonical `mrea.contracts.v1` and canonical fixtures remain unchanged.
