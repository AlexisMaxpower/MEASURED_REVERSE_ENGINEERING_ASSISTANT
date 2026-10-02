# ORCHESTRATOR DIRECTIVE — Chat 1

**Revision:** `OD-2026-10-02-011`  
**Control owner:** central orchestration  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes all older Chat-1 directives.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_18_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch from the then-current shared `main` containing the Round-18 closure state;
4. do not use a historical Pass-18 worker or integration branch as the implementation base.

## Slice ownership

Chat 1 owns Project & Guided Capture. Preserve explicit recapture lineage, immutable clean-reference truth, attributable provenance and canonical-contract ownership. Voice triggers remain capture-control provenance only and must not create metrology truth. Preparation/setup guidance remains operator readiness evidence; it must stay separate from physical measurement truth and must fail closed before capture-state mutation when required readiness is absent or failed.

## Standing SOLIDWORKS qualification

SOLIDWORKS real-host qualification is out-of-band. Do not copy historical per-round host-gate status into Chat-1 handoffs.

## Next pass rule

Execute the active worker-round/user task for Chat 1. If no current task exists, stop rather than reviving an historical task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-1 plus adjacent boundary/contract gates, publish exact SHA/CI evidence, and do not merge directly to `main`.
