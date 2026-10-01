# ORCHESTRATOR DIRECTIVE — Chat 5

**Revision:** `OD-2026-09-30-004`  
**Owner:** Chat 6  
**Central round:** 4  
**Selected worker cut:** `chat-5/pass-8` @ `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`

## Accepted central baseline

Round 3 is closed. Chat 5 Pass 3 is accepted in `main`.

Round-4 plan:

`chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`

## Selected cumulative input

Chat 6 selects the frozen `chat-5/pass-8` cumulative branch for Round-4 Stage-1 review.

The cumulative worker stack advances lifecycle/persistence/read-only engineering knowledge through snapshot-bound deterministic pagination.

The Pass-8 handoff is treated as the freeze point pending independent Chat-6 review.

## OD-004 task

No new normal worker implementation is requested now.

Keep `chat-5/pass-8` frozen unless Chat 6 returns explicit `FIX_REQUIRED`.

Chat 6 will independently review and replay only accepted Chat-5-owned changes onto the current shared baseline.

## Required truth invariants under review

- manufacturing eligibility remains derived from canonical CAD verification facts;
- CAD mismatch/unverified states cannot be promoted to eligible by lifecycle or knowledge code;
- physical-instance lifecycle transitions remain deterministic and fail closed;
- failure evidence remains tied to exact physical instances/revisions;
- read-only/knowledge projections operate on committed factual lifecycle state;
- query aggregation/pagination does not invent engineering conclusions or quality rankings;
- snapshot-bound cursors cannot silently continue against another snapshot/filter set;
- historical facts are not silently rewritten by later projections.

## Round-4 boundary focus

Chat4->Chat5 must prove:

```text
CAD VERIFIED/MISMATCH/UNVERIFIED
-> manufacturing eligibility
-> physical lifecycle facts
-> read-only/knowledge projections
```

Vendor success alone is not sufficient input for manufacturing eligibility.

## Required gates

During central review/replay the selected cut must keep green:

- `Chat 5 / Lifecycle`;
- `Integration / Chat 4 -> Chat 5`;
- canonical contracts/fixtures.

## Do not

- push Pass 9 work onto the selected frozen cut;
- import SOLIDWORKS-specific types into lifecycle/knowledge models;
- convert factual counts/patterns into unsupported recommendations or rankings;
- modify Chat-6-owned CI/shared integration tests;
- change canonical contracts without approved CR;
- merge directly to `main`.

## Current state

```text
CHAT_5_PASS_8 = FROZEN_SELECTED_FOR_ROUND4_STAGE1
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```
