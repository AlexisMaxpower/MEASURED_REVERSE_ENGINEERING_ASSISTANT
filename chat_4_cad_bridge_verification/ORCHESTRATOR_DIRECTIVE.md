# ORCHESTRATOR DIRECTIVE — Chat 4
**Revision:** OD-2026-09-29-002  
**Owner:** Chat 6
**Pass:** 2  
**Branch:** `chat-4/pass-2`

## Accepted from Pass 1
Generic CAD mapping/export/verification gate is accepted structurally.

`CHANGE_REQUEST_002_SOLIDWORKS_ENVIRONMENT.md` is resolved by `chat_6_orchestrator/ADR_001_SOLIDWORKS_2026_CAD_AGENT.md`.

## Pass 2 priority
Begin the real SOLIDWORKS 2026 adapter path behind the already-tested vendor-neutral boundary.

Baseline:
- Windows 11 x64;
- SOLIDWORKS 2026 x64;
- C# / .NET Framework 4.8;
- STA COM;
- separate user-session CAD Agent process;
- SOLIDWORKS interop references isolated inside the vendor adapter;
- canonical read-back normalized to mm/deg.

Required:
- create the production C# adapter/agent project structure without changing canonical semantics;
- keep `dimension_id ↔ measurement_id ↔ vendor_dimension_ref` traceability;
- make COM lifecycle/error handling explicit;
- keep generic TEST_DOUBLE/SVG/DXF tests runnable without SOLIDWORKS;
- document the first real-host integration procedure.

## CI requirement
GitHub-hosted CI must keep the generic Chat 4 CAD gate green. Real SOLIDWORKS COM execution is an environment-only gate and is not required on public GitHub-hosted runners. Push Pass 2 only to `chat-4/pass-2` and record both generic CI status and real-host test status in handoff.

## Do not
- move SOLIDWORKS types into canonical contracts/domain;
- weaken numerical read-back verification;
- require installed SOLIDWORKS for generic/unit tests;
- commit Pass 2 implementation directly to `main`.

## Handoff
Finish with `ORCHESTRATOR_HANDOFF.md` per Chat 6 development workflow.
