# Chat 4 — Pass 13 Dimension-Shape Capability Handshake

**Date:** 2026-10-01  
**Branch:** `chat-4/pass-13`  
**Worker base:** shared `main@4edde5c644755734a2ccf6e8f1c1b6ab9a63424d`

## Purpose

Round 12 introduced a worker capability fingerprint for declared entity types, verified dimension types/units, constraints, adapter identity and the SOLIDWORKS agent protocol. Its accepted scope explicitly did not yet fingerprint verified-dimension arity/entity-combination rules.

Pass 13 closes that specific gap without changing shared canonical contracts.

## Slice-local dimension capability contract

`src/mrea_cad_bridge/solidworks_dimension_capabilities.py` defines `mrea.solidworks-dimension-rules.v1`.

The declared fail-closed subset is:

| Dimension | Unit | Entity pattern |
| --- | --- | --- |
| `DISTANCE` | `mm` | one `LINE`, or two `CIRCLE`/`ARC` entities |
| `DIAMETER` | `mm` | exactly one `CIRCLE` |
| `RADIUS` | `mm` | exactly one `CIRCLE` or `ARC` |
| `ANGLE` | `deg` | exactly two non-parallel `LINE` entities |

Additional rules:

- entity IDs inside one dimension must be distinct;
- all referenced entity IDs must exist;
- `ANGLE` requires `0 < value < 180`;
- `ANGLE` non-parallel validation uses normalized cross-product threshold `1e-10`.

The evaluator returns machine-readable failure codes and is used directly by the Python SOLIDWORKS request preflight.

## Worker fingerprint

The worker capability projection now includes the complete `verified_dimension_rules` object in addition to the Round-12 fields.

Current Pass-13 worker SHA-256:

```text
756c37d781e051f0f5b0285a451dc53d2d9d90e98ad3e7b4bfa94924d88dd974
```

A dimension-rule edit therefore changes the Python fingerprint and requires an intentional matching C# worker update.

## C# pre-COM validation

`Program.ValidateRequestEnvelope(...)` now invokes `ValidateDimensionEnvelope(request)` after protocol/fingerprint/basic-field validation and before `SolidWorksSession.Open(request)`.

The envelope validates the same supported type/unit/entity-pattern subset, duplicate references, ANGLE range and ANGLE non-parallel geometry.

Unsupported verified dimensions fail with request-invalid semantics (`exit 20`) before SOLIDWORKS COM startup and before CAD mutation.

`SolidWorksTransfer.ValidateSlice(...)` remains an additional deeper worker validation layer; Pass 13 does not remove downstream guards.

## Tests

Pass 13 adds `tests/test_solidworks_dimension_capabilities.py` covering accepted and rejected dimension patterns, duplicate/unknown references, type-specific units, ANGLE range, parallel geometry and degenerate geometry.

`tests/test_solidworks_worker_handshake.py` also proves:

- the worker fingerprint contains the dimension-rule contract;
- Python and C# embed the same new SHA-256;
- dimension envelope validation occurs before COM startup;
- C# envelope contains the declared DISTANCE/DIAMETER/RADIUS/ANGLE structural rules;
- the ANGLE normalized-cross threshold matches the fingerprinted declaration.

## Scope limit

This pass hardens verified-dimension structural compatibility only. It does not claim complete C# behavioral equivalence and does not fingerprint every runtime operation such as SOLIDWORKS selection behavior, solver behavior, rebuild behavior, SaveAs behavior or native read-back implementation.

It also does not change `mrea.contracts.v1`; these are vendor-specific fail-closed restrictions layered on top of the canonical SketchDimension schema.

## Standing host qualification

This software-only pass does not itself produce real-host qualification. The operational source of truth remains the dedicated workflow:

```text
SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY
QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml
ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE
```

Pass 13 changes fingerprinted host-boundary files (`solidworks_agent/Program.cs`, `src/mrea_cad_bridge/solidworks_agent.py`, and `src/mrea_cad_bridge/solidworks_worker_handshake.py`) and introduces `src/mrea_cad_bridge/solidworks_dimension_capabilities.py`. Orchestrator 1 therefore adds that new capability file to the standing qualification fingerprint set.

Any successful qualification generated for an earlier host-boundary fingerprint does not positively qualify this changed boundary. Re-run the dedicated host workflow when a positive SOLIDWORKS host qualification is required. Ordinary software CI cannot promote that status, and lack of a current positive host qualification is not an ordinary software-round blocker.
