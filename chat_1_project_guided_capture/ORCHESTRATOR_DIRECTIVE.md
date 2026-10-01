# ORCHESTRATOR DIRECTIVE — Chat 1

**Revision:** `OD-2026-09-30-004`  
**Owner:** Chat 6  
**Central round:** 4  
**Worker target branch:** `chat-1/pass-4`

Read before further work.

## Accepted central baseline

Round 3 is closed on the certified software baseline. Chat 1 Pass 3 is accepted in `main`.

Current Round-4 plan:

`chat_6_orchestrator/PASS_4_PLAN_2026-09-30.md`

## Observed Pass-4 state

Observed branch head:

`beed09508c8cba294b1e78d7b6b7f3226f72d734`

Observed implementation includes immutable clean-reference recapture lineage and source/supersession relationships.

Problem:

`chat-1/pass-4` still contains an `ORCHESTRATOR_HANDOFF.md` that identifies Pass 3 / `chat-1/pass-3`.

Therefore the current Pass-4 branch is not yet a protocol-valid frozen Stage-1 input.

## OD-004 task

Do **not** start another feature pass.

Finish the existing Pass 4 as a reviewable worker result:

1. inspect the current Pass-4 implementation against the accepted Round-3 baseline and current canonical contracts;
2. correct only defects necessary for a truthful Pass-4 result;
3. run the required Chat-1 slice and Chat1->Chat2 boundary gates against the current repository/shared baseline where possible;
4. publish a new Pass-4 `ORCHESTRATOR_HANDOFF.md` that records:
   - exact branch;
   - exact implementation/pre-handoff SHA;
   - CI run IDs/results;
   - exact delivered scope;
   - changed files;
   - provenance/immutability invariants;
   - known limitations;
   - explicit freeze state;
5. after that handoff commit, freeze `chat-1/pass-4`.

## Required truth invariants

- clean-reference recapture must be explicit lineage, not silent replacement;
- measurement/reference provenance must remain attributable to the correct clean-reference generation;
- existing verified physical facts must not be mutated by a later recapture;
- `CapturePackage v1` compatibility must remain intact unless Chat 6 approves a Change Request;
- no measurement, geometry or CAD ownership moves into Chat 1.

## Required gates

Keep green:

- `Chat 1 / Capture`;
- `Integration / Chat 1 -> Chat 2`;
- canonical contracts/fixtures.

## Do not

- start Pass 5;
- modify Chat-6-owned CI/shared integration tests;
- modify `core/contracts` without approved CR;
- merge to `main`;
- claim Stage-1 acceptance before Chat 6 review.

## Completion state

Expected final worker state:

```text
CHAT_1_PASS_4 = HANDOFF_PUBLISHED_AND_FROZEN
ROUND_4_STAGE1_ACCEPTANCE = PENDING_CHAT6
```
