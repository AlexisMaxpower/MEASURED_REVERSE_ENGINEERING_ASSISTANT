# Chat 4 — Pass 9 SOLIDWORKS Capability Manifest

**Date:** 2026-09-30  
**Branch:** `chat-4/pass-9`  
**Baseline:** Pass 8 `236b4487471e4eb149eb7dd9539474a9d4ca06c0`

## Scope

Pass 9 adds a machine-readable, slice-local capability manifest for the current SOLIDWORKS vendor path.

It does **not** change canonical/shared contracts and does not infer real-host success.

## Why

Until this pass, callers learned many vendor limitations only by attempting a transfer and receiving a fail-closed error. The new manifest lets orchestration/UI code discover the current supported subset before invoking the worker.

## Contract

New slice-local schema identifier:

`mrea.solidworks-capabilities.v1`

Public API:

- `build_solidworks_capabilities_v1()`;
- `is_solidworks_constraint_supported_v1(...)`.

## Declared current capability

Geometry entities:

- POINT;
- LINE;
- CIRCLE;
- ARC.

Verified dimensions:

- DISTANCE — mm;
- DIAMETER — mm;
- RADIUS — mm;
- ANGLE — deg.

Verified constraints currently implemented by the worker:

- HORIZONTAL;
- VERTICAL;
- PARALLEL;
- PERPENDICULAR;
- CONCENTRIC;
- EQUAL (LINE/LINE only).

Explicitly unsupported in the current MREA worker:

- COINCIDENT;
- TANGENT;
- SYMMETRIC.

The manifest explains the reason for every unsupported relation. In particular, SOLIDWORKS itself supports `sgTANGENT`, but the current MREA worker does not claim it until it is actually implemented and validated in the vendor path.

## Runtime truth

The capability manifest is descriptive, not runtime evidence.

It therefore explicitly reports:

```text
REAL_HOST = UNVERIFIED
C# PRODUCTION BUILD = UNVERIFIED
REAL_HOST_GATE = EXTERNAL_EVIDENCE_REQUIRED
```

A capability manifest cannot promote runtime state to VERIFIED.

## Tests

New `tests/test_solidworks_capabilities.py` covers:

- stable schema/adapter identity;
- full geometry declaration;
- dimension/unit declaration;
- current supported constraint subset;
- explicit unsupported constraint subset;
- TANGENT not falsely advertised;
- non-VERIFIED constraint status rejected by capability query;
- verified supported constraint query;
- no real-host VERIFIED claim;
- deep-copy isolation for callers.

## Remaining work

- implement and host-validate TANGENT before moving it to `supported`;
- define deterministic canonical endpoint/sub-entity semantics before COINCIDENT;
- define deterministic symmetry-axis semantics before SYMMETRIC;
- keep manifest synchronized with real worker behavior through regression tests.
