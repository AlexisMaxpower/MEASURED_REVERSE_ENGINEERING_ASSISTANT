# ORCHESTRATOR DIRECTIVE — Chat 2

**Revision:** `OD-2026-10-01-006`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-2 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main`;
4. do not use a historical pass/readiness branch as the implementation base.

## Slice ownership

Chat 2 owns Physical Measurement. Preserve measurement provenance, explicit confirmation, uncertainty truth, raw anchors and the rule that downstream AI/geometry/CAD cannot silently rewrite verified physical facts.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy the historical three `UNVERIFIED` host labels into Chat-2 handoffs. Refer to `chat_6_orchestrator/SOLIDWORKS_HOST_QUALIFICATION_POLICY.md` only if the active task explicitly concerns that qualification.

## Next pass rule

Execute the active worker-round/user task for Chat 2. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-2 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
