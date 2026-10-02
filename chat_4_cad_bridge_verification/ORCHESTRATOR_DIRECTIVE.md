# ORCHESTRATOR DIRECTIVE — Chat 4

**Revision:** `OD-2026-10-02-010`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-4/4B directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. read `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md`;
3. require `ROUND_17_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
4. branch from the then-current shared `main` containing the Round-17 closure state;
5. do not use a historical Chat-4/4B pass or integration branch as the implementation base.

## Slice ownership

Chat 4 owns CAD Bridge & Verification, including generic CAD transfer/verification and SOLIDWORKS-specific behavior behind the vendor/process boundary.

Preserve these invariants:

- canonical verification remains vendor-neutral;
- `ArtifactReference` normalization follows the actual canonical v1 field set: required `artifact_id`, `kind`, `uri`; optional `media_type`, `sha256`, `metadata`; unknown top-level fields fail closed;
- response evidence remains request-correlated, complete and uniquely identified;
- constraint conflicts take precedence over numeric read-back and cannot silently become VERIFIED;
- unsupported vendor cases fail closed;
- SOLIDWORKS rebuild failure after relation creation or before native save/read-back is a transfer failure, never success evidence;
- real-host execution is never inferred from Linux CI, static checks, mocks or test doubles;
- capability/protocol/entity/dimension/constraint checks occur before CAD mutation where designed;
- fingerprinted host-boundary changes invalidate reuse of mismatched standing qualification evidence;
- canonical contracts/shared CI are not changed without approved central ownership.

## Standing SOLIDWORKS host qualification

The per-round host-gate carry-forward remains retired. Real-host truth is owned only by the standing `SOLIDWORKS_HOST_QUALIFICATION` workflow and matching fingerprinted evidence. Round 17 changed `SolidWorksTransfer.cs`; do not reuse an older positive qualification unless its source/boundary fingerprint matches current `main` and the controlled host remains materially unchanged.

## Next pass rule

Execute the active worker-round/user task for Chat 4. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-4 generic plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`. Mention standing host qualification only when its state/fingerprint is actually relevant to the pass.
