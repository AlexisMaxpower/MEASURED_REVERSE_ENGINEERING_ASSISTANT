# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-10-01-007`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-4/4B directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. read `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`;
3. require `ROUND_13_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
4. branch from the then-current shared `main` containing the Round-13 closure state;
5. do not use a historical Chat-4/4B pass branch as the implementation base.

## Slice ownership

Chat 4 owns CAD Bridge & Verification, including generic CAD transfer/verification and SOLIDWORKS-specific behavior behind the vendor/process boundary.

Preserve these invariants:

- canonical verification remains vendor-neutral;
- unsupported vendor cases fail closed;
- vendor/process success alone does not promote canonical verification;
- real-host execution is never inferred from Linux CI, static checks, mocks or test doubles;
- capability/protocol compatibility checks occur before CAD mutation where designed;
- dimension-shape capability rules remain fingerprinted into standing host qualification;
- canonical contracts/shared CI are not changed without an approved central change.

## Standing SOLIDWORKS host qualification

The per-round host-gate carry-forward is retired. Real-host truth is owned only by the standing `SOLIDWORKS_HOST_QUALIFICATION` workflow and its fingerprinted evidence.

Round 13 changed the fingerprinted SOLIDWORKS host boundary. Any previous positive qualification may be reused only when its recorded fingerprint matches the current boundary and the controlled host has not materially changed. Never promote software CI into real-host qualification.

## Next pass rule

Execute the active worker-round/user task for Chat 4. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-4 generic plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`. Mention standing host qualification only when its state/fingerprint is actually relevant to the pass.
