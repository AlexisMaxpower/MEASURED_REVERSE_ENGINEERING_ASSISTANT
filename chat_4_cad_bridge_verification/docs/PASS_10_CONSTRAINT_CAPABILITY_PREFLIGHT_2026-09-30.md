# Chat 4 — Pass 10 Constraint Capability Preflight

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-10`  
**Continuation baseline:** `7bda3632b41db5739bc7c411b4a9aac616221cf1`

## Repository state checked before work

The common repository was re-read before this continuation.

- `main`: `c034f7583d4e1f130f827d94a43762f3cad1a7e5`;
- selected Round-4 Chat-4 cut remains `chat-4/pass-7` and is `ACCEPTED / FROZEN`;
- current integration candidate: `integration/pass-4-candidate` at `b5fdcd6324efd1396a3d57a28fc11e0dd0ba4afd`;
- Chat 4 is not reopened by the central Round-4 fix cycle;
- this work therefore continues only the user-authorized isolated `chat-4/pass-10` branch and does not modify the frozen Pass-7 branch, shared CI, canonical contracts, or another slice.

## Scope

Pass 10 now exposes the exact SOLIDWORKS constraint compatibility decision as a machine-readable preflight API instead of forcing callers to discover geometry/status failures only by attempting a transfer.

Public API:

- `SolidWorksConstraintSupportDecision`;
- `evaluate_solidworks_constraint_support_v1(constraint, entities_by_id)`.

Decision fields:

- `supported`;
- `code`;
- `constraint_id`;
- `constraint_type`;
- `status`;
- `entity_ids`;
- `entity_types`;
- `message`.

Current reason codes:

- `SUPPORTED`;
- `STATUS_NOT_VERIFIED`;
- `TYPE_UNSUPPORTED`;
- `ENTITY_IDS_INVALID`;
- `ENTITY_IDS_DUPLICATE`;
- `ENTITY_UNKNOWN`;
- `ARITY_UNSUPPORTED`;
- `GEOMETRY_UNSUPPORTED`.

## Single-source preflight

`solidworks_agent.py` no longer maintains a second independent constraint-compatibility implementation. Vendor request preflight calls the public capability evaluator and converts any unsupported decision into `CadAdapterError` containing the machine-readable decision code.

This keeps manifest/query behavior and actual adapter preflight aligned for:

- HORIZONTAL;
- VERTICAL;
- PARALLEL;
- PERPENDICULAR;
- CONCENTRIC;
- EQUAL;
- TANGENT.

`COINCIDENT` and `SYMMETRIC` remain unsupported. No endpoint/sub-entity semantics are invented.

## Truth boundaries

This change is preflight/capability logic only.

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
NATIVE SLDPRT GENERATION/READBACK = UNVERIFIED
```

No canonical verification status is promoted by capability evaluation.
