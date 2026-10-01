# ORCHESTRATOR DIRECTIVE — Chat 2

**Revision:** `OD-2026-10-01-005`  
**Control owner:** central orchestration  
**Issued as:** Round-12 final control-plane repair by Orchestrator 2  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes `OD-2026-09-30-004` and every historical instruction that pins Chat 2 to `chat-2/pass-6` or forbids work beyond the old Round-4 selected cut.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch the new worker pass from the then-current shared `main`;
4. do not reuse `chat-2/pass-6`, verification-only Pass 10/11/12 branches, or another historical pass as the implementation base.

Round 12 imported no Chat-2 product delta; `chat-2/pass-12-readiness` was diagnostic/control evidence only. The current integrated Chat-2 product/test surface on `main` remains authoritative.

## Slice ownership

Chat 2 owns Physical Measurement: measurement types/units, raw anchors, manual/device/OCR/voice proposals, explicit confirmation/verification, uncertainty and physical-measurement provenance within the existing shared contract.

Preserve these invariants:

- raw measurement anchors remain attributable to their capture/reference evidence;
- candidates do not become verified without explicit allowed confirmation;
- uncertainty remains in the measurement's own canonical unit and is never fabricated;
- verified physical values/provenance are not silently rewritten by AI, geometry or CAD;
- downstream coordinate normalization remains outside Chat 2;
- canonical contracts/shared CI are not changed without an approved central change.

## Next pass rule

This control document intentionally does not invent the next feature. Execute the active worker-round/user task for Chat 2 after resolving the current certified `main`. If no current task exists, stop rather than reviving an old OD-004 task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-2 plus Chat1->Chat2/Chat2->Chat3 and contract gates as applicable, publish a truthful handoff with exact SHA/CI evidence, and do not merge directly to `main`.
