# Chat 4 — Build / Reuse Check: SOLIDWORKS 2026 CAD Agent

**Pass:** 2  
**Directive:** `OD-2026-09-29-002`  
**ADR:** `chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`

## Problem

MREA needs a real SOLIDWORKS 2026 transfer path without moving COM/vendor semantics into canonical contracts or making ordinary unit tests require SOLIDWORKS.

## Existing solution / reuse

**PARTIAL / YES for vendor API.**

Use the official installed SOLIDWORKS 2026 API/COM interop assemblies and public API. Do not build a CAD kernel, COM replacement, DXF parser, or redistribute proprietary interop DLLs in the repository.

Official API references used for implementation decisions:

- SOLIDWORKS API 2026 namespace/help: `https://help.solidworks.com/2026/English/api/sldworksapi/`
- API SDK / local interop references: `https://help.solidworks.com/2026/english/api/sldworksapiprogguide/GettingStarted/SOLIDWORKS_API_SDK.htm`
- system requirements: `https://www.solidworks.com/support/system-requirements`

## What is custom MREA code

- slice-local JSON process protocol between Python adapter and C# agent;
- out-of-process invocation/lifecycle boundary;
- `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` mapping;
- mm/deg ↔ SOLIDWORKS system-unit normalization;
- unresolved-input preflight;
- native artifact projection back into existing `CADPackage.artifacts`;
- real-host golden runner.

## Runtime topology

```text
canonical SketchPackage
→ Python SolidWorksAgentAdapter
→ one-shot C# .NET Framework 4.8 x64 STA process
→ SOLIDWORKS 2026 COM/API
→ slice-local normalized JSON response
→ existing CadAdapterResult
→ existing VerificationEngine
→ canonical CADPackage/CADVerificationReport
```

## Lock-in

Vendor code is intentionally SOLIDWORKS-specific but isolated. Canonical contracts and verification remain vendor-neutral. A future different CAD agent can implement the same normalized `CadAdapter` semantics.

## Failure policy

- no SOLIDWORKS host: `UNVERIFIED`, not PASS;
- unsupported geometry/constraint/dimension: explicit failure;
- unresolved input touching a verified dimension: preflight failure before COM;
- partial COM transfer/save/read-back: adapter failure, not verification success;
- no silent manufacturing-tolerance substitution for numerical-transfer tolerance.

## Current Pass 2 slice

Real agent handles the golden fixture subset (`LINE`, `CIRCLE`, DISTANCE, DIAMETER; RADIUS supported by worker path). POINT/ARC/ANGLE and canonical constraints remain explicit future work and are not approximated.
