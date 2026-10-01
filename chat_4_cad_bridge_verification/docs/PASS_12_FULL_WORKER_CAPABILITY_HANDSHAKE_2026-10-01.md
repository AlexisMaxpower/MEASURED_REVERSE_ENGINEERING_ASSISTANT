# Chat 4 — Pass 12 Full Worker Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-12`  
**Base:** current shared `main` at `c888704b37e88b68c055f1095e6e9a4fc3650f7e`

## Purpose

Pass 11 protected the Python adapter -> C# SOLIDWORKS worker boundary against constraint-matrix drift. That still left a fail-open compatibility gap if Python and the worker disagreed about geometry support, verified dimension support/units, adapter identity, or the agent protocol while the constraint subset itself stayed unchanged.

Pass 12 adds a second, broader fingerprint over the complete worker-relevant capability projection.

## Worker compatibility projection

The deterministic projection contains only facts that must stay identical across the Python preflight and C# worker:

- capability schema version;
- adapter identity;
- supported geometry entity types;
- supported verified dimension types and units;
- the full constraint support/limitation object;
- the SOLIDWORKS agent protocol version.

It intentionally excludes runtime/external-evidence state and unrelated side protocols. A later real-host result must not invalidate a worker binary solely because runtime evidence changed.

Current worker capability SHA-256:

```text
1713a8671cc358c54af5664fb1144789ba85b50291d2b02e479aa568a14ae4bd
```

## Protocol behavior

Python now sends both:

```text
worker_capabilities_sha256
constraint_capabilities_sha256
```

The broader worker fingerprint is checked first in `Program.ValidateRequestEnvelope(...)`. The Pass-11 constraint fingerprint remains as an additional narrow guard and backward audit signal.

A missing or mismatched worker fingerprint fails with invalid-input semantics before `SolidWorksSession.Open(request)` and therefore before any COM startup or CAD mutation.

## Test guard

`tests/test_solidworks_worker_handshake.py` verifies:

1. deterministic expected full-worker SHA-256;
2. the exact projection scope;
3. caller-safe projection snapshots;
4. Python request propagation of both fingerprints;
5. exact Python/C# worker hash parity;
6. validation before SOLIDWORKS COM startup;
7. C# protocol-model field parity.

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
