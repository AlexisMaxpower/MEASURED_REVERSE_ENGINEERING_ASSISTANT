# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-10-02-011`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-4/4B directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. read `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`;
3. require `ROUND_18_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
4. branch from the then-current shared `main` containing the Round-18 closure state;
5. do not use a historical Chat-4/4B Pass-18 or integration branch as the implementation base.

## Slice ownership

Chat 4 owns CAD Bridge & Verification, including generic CAD transfer/verification and SOLIDWORKS-specific behavior behind the vendor/process boundary.

Preserve these invariants:

- canonical verification remains vendor-neutral;
- unsupported vendor cases fail closed;
- vendor/process success alone does not promote canonical verification;
- native SOLIDWORKS artifact evidence must be correlated to the current sketch-package/request identity rather than accepted from a stale or foreign request;
- response evidence must remain request-correlated, complete and uniquely identified;
- constraint conflicts take precedence over numeric read-back and cannot silently become VERIFIED;
- real-host execution is never inferred from Linux CI, static checks, mocks or test doubles;
- capability/protocol/entity/dimension/constraint checks occur before CAD mutation where designed;
- SOLIDWORKS rebuild failures and non-finite/unexpected system-value read-back fail closed before positive evidence or native-save success is accepted;
- fingerprinted host-boundary changes invalidate reuse of mismatched standing qualification evidence;
- canonical contracts/shared CI are not changed without approved central ownership.

## Standing SOLIDWORKS host qualification

The per-round host-gate carry-forward remains retired. Real-host truth is owned only by the standing `SOLIDWORKS_HOST_QUALIFICATION` workflow and fingerprinted evidence. Round 18 changed fingerprinted boundary source including `solidworks_agent.py` and `SolidWorksTransfer.cs`; do not reuse older positive qualification unless its fingerprint matches the current boundary and the controlled host remains materially unchanged.

## Next pass rule

Execute the active worker-round/user task for Chat 4. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-4 generic plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`. Mention standing host qualification only when its state/fingerprint is actually relevant to the pass.
