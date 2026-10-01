# Chat 4 — Pass 12 Worker Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-12`  
**Base:** shared `main` at `c888704b37e88b68c055f1095e6e9a4fc3650f7e`

## Purpose

Pass 11 protected the Python adapter -> C# SOLIDWORKS worker boundary against constraint-matrix drift. That still left a fail-open compatibility gap if Python and the worker disagreed about the declared geometry support, verified dimension support/units, adapter identity, or the agent protocol while the constraint subset itself stayed unchanged.

Pass 12 adds a second, broader fingerprint over the worker-relevant **declared capability projection**.

## Worker compatibility projection

The deterministic projection contains declared facts that must stay identical across the Python preflight and C# worker:

- capability schema version;
- adapter identity;
- supported geometry entity types;
- supported verified dimension types and units;
- the constraint support/limitation object;
- the SOLIDWORKS agent protocol version.

It intentionally excludes runtime/external-evidence state and unrelated side protocols. A later real-host result must not invalidate a worker binary solely because runtime evidence changed.

Current worker capability SHA-256:

```text
1713a8671cc358c54af5664fb1144789ba85b50291d2b02e479aa568a14ae4bd
```

## Protocol behavior

Python sends both:

```text
worker_capabilities_sha256
constraint_capabilities_sha256
```

The broader worker fingerprint is checked first in `Program.ValidateRequestEnvelope(...)`. The Pass-11 constraint fingerprint remains as an additional narrow guard and backward audit signal.

A missing or mismatched worker fingerprint fails with invalid-input semantics before `SolidWorksSession.Open(request)` and therefore before any COM startup or CAD mutation.

## Implementation binding

The fingerprint is tied to the declared support matrix rather than being a disconnected constant:

- Python `_SUPPORTED_ENTITY_TYPES` and `_SUPPORTED_DIMENSION_TYPES` are derived directly from `build_solidworks_worker_capability_projection_v1()`;
- CI reads `SolidWorksTransfer.cs` and verifies that its top-level entity-type guard, dimension-type guard, unit guards and `RelationId(...)` constraint mapping agree with the declared projection used to calculate the fingerprint.

This catches drift in those explicitly checked surfaces.

## Important scope limit

This is **not** a cryptographic fingerprint of every executable C# behavior. The current projection does not encode every structural/runtime rule enforced by `SolidWorksTransfer.cs`, including examples such as:

- entity coordinate/radius/arc-span validity;
- dimension arity and entity-combination rules;
- ANGLE numeric range and non-parallel-line requirements;
- vendor API call behavior, selection semantics, rebuild behavior or save/read-back behavior.

A future implementation-only change outside the explicitly checked support-matrix surfaces can therefore require an additional test/projection update even when `worker_capabilities_sha256` itself would otherwise remain unchanged. The handshake proves declared compatibility for the fingerprinted surface; it does not prove full behavioral equivalence of Python and C# implementations.

## Test guard

`tests/test_solidworks_worker_handshake.py` verifies:

1. deterministic expected worker SHA-256;
2. the exact declared projection scope;
3. caller-safe projection snapshots;
4. Python preflight entity/dimension sets are derived from the projection;
5. Python request propagation of both fingerprints;
6. exact Python/C# worker hash parity;
7. validation before SOLIDWORKS COM startup;
8. C# top-level entity and dimension type guards match the declared projection;
9. C# linear/angular unit guards agree with the declared units;
10. C# relation mapping matches every declared supported constraint;
11. C# protocol-model field parity.

## Ownership / contract boundary

This pass changes only Chat-4-owned SOLIDWORKS adapter/worker files and tests. It does not change shared canonical contracts, shared integration tests, GitHub workflows, or another slice.

Canonical CAD verification remains vendor-neutral and unchanged.

## External truth

This pass is static/protocol hardening only. It does not represent a controlled Windows/SOLIDWORKS execution.

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```
