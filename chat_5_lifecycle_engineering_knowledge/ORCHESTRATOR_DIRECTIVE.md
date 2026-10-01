# ORCHESTRATOR DIRECTIVE — Chat 5

**Revision:** `OD-2026-10-01-005`  
**Control owner:** central orchestration  
**Issued as:** Round-12 final control-plane repair by Orchestrator 2  
**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`

This directive supersedes `OD-2026-09-30-004` and every historical instruction that pins Chat 5 to `chat-5/pass-8`, Round-4 replay or an old frozen cut.

## Required baseline

Before starting the next worker pass:

1. read `chat_6_orchestrator/ORCHESTRATION_STATE.md`;
2. require `ROUND_12_CLOSED = TRUE` and `NEXT_FULL_WORKER_PASS = READY`;
3. branch the new worker pass from the then-current shared `main`;
4. do not reuse a historical Chat-5 pass branch as the implementation base.

Round 12 integrates snapshot-synchronized materialized analytical aggregates for revision outcomes and failure patterns, while preserving snapshot-bound cursor semantics and the legacy v1 cursor path.

## Slice ownership

Chat 5 owns Lifecycle & Engineering Knowledge: manufacturing eligibility, physical lifecycle state, durable persistence/read models, factual engineering knowledge queries and their deterministic pagination semantics.

Preserve these invariants:

- manufacturing eligibility remains derived from canonical CAD verification/runtime facts;
- CAD mismatch/unverified state cannot be promoted by lifecycle/knowledge code;
- lifecycle transitions and persistence remain deterministic and fail closed;
- knowledge projections summarize committed facts without inventing causality, rankings or recommendations;
- snapshot-bound cursors cannot continue silently against another snapshot/filter set;
- historical facts are not silently rewritten by later projections;
- canonical contracts/shared CI are not changed without an approved central change.

## Next pass rule

This control document intentionally does not invent the next feature. Execute the active worker-round/user task for Chat 5 after resolving the current certified `main`. If no current task exists, stop rather than reviving an old OD-004 task.

## Delivery rule

Use a new pass branch from current `main`, run Chat-5 plus Chat4->Chat5 and contract gates as applicable, publish a truthful handoff with exact SHA/CI evidence, and do not merge directly to `main`.
