# Chat 4 — Pass 11 Constraint Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-11`  
**Base:** Pass-10 final worker handoff `6288d9df98a8343f529e86daf0f8dc03c2f0679a`

## Purpose

Pass 11 closes a version-drift gap at the Python adapter -> C# SOLIDWORKS worker boundary.

Pass 10 made Python constraint preflight machine-readable and fail-closed, but an older/mismatched C# worker binary could still carry a different supported-constraint matrix while accepting the same `mrea.solidworks-agent.v1` envelope.

Pass 11 adds a deterministic constraint-capability fingerprint handshake.

## Handshake

Python computes SHA-256 over canonical JSON for the exact `constraints` capability object from `mrea.solidworks-capabilities.v1`:

```text
02a33af48298669e3563ce467b6cd6d8f2586d073baa3de6baa45749fc92a3d8
```

`build_solidworks_agent_request(...)` includes:

```json
"constraint_capabilities_sha256": "02a33af48298669e3563ce467b6cd6d8f2586d073baa3de6baa45749fc92a3d8"
```

The C# request model carries the same field. `Program.ValidateRequestEnvelope(...)` compares it against the worker's embedded expected fingerprint before `SolidWorksSession.Open(request)` is called.

Missing or mismatched fingerprints fail as invalid input before SOLIDWORKS COM startup.

## Why only constraints are fingerprinted

This handshake protects the surface most likely to drift between the Python preflight and the vendor relation mapper:

- supported relation types;
- explicitly unsupported relation types;
- required constraint status;
- geometry limitations.

Runtime host status and unrelated protocol metadata are intentionally excluded from this fingerprint.

## CI drift guard

Python tests verify:

1. deterministic expected SHA-256;
2. request propagation;
3. exact C# embedded fingerprint parity;
4. C# mismatch check occurs before COM startup;
5. C# protocol model contains the fingerprint field.

A future constraint-capability change must therefore update both sides deliberately or CI fails.

## Scope/truth boundary

No canonical contract or shared integration surface changes.

```text
REAL_SOLIDWORKS_2026_HOST = UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

The handshake prevents stale adapter/worker capability combinations; it does not itself prove a real SOLIDWORKS host execution.
