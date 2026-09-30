# ROUND 3 — NEXT_ROUND_INPUT

**Owner:** Chat 8 — Deputy Orchestrator 2 / Final Certifier  
**Date:** 2026-09-30  
**Protocol role:** input to Chat 6 for planning the next central round  
**Status:** `NEXT_ROUND_INPUT_READY_FOR_CHAT6`

## 1. Boundary of this document

This is not a Round-4 plan and does not accept any Pass-4+ worker branch.

Per the deputy-orchestrator protocol, Chat 8 closes the current round and records unresolved risks, external gates, architectural concerns and suggested priorities. Chat 6 owns the actual next-pass design, directives, Stage-1 review and merge plan.

## 2. Certified baseline after Round 3

Final accepted software baseline:

- `main` SHA: `bffc1dec2fe63c12b69a50c4bf348ef7df4cf662`;
- `main` tree: `435dda140d3980256ca32c42bd07d81b15c4328c`;
- certified Round-3 candidate: `1c9ccb432664e57a24be8fe586bb07ad13fd5075`;
- post-merge MREA CI run: `36651010221`;
- post-merge CI conclusion: `SUCCESS`;
- post-merge Round-3 golden path: `SUCCESS`.

The real vendor runtime gate remains outside this certification:

```text
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
C# PRODUCTION BUILD ON CONTROLLED WINDOWS/SOLIDWORKS HOST = UNVERIFIED
NATIVE .SLDPRT GENERATION + READ-BACK = UNVERIFIED
```

## 3. Orchestration baseline concern on current main

`chat_6_orchestrator/ORCHESTRATION_STATE.md` on current `main` is stale relative to the certified repository state. It still reports:

```text
Directive revision: OD-2026-09-29-003
Status: Round 2 ACCEPTED — software integration GREEN; Pass 3 preparation active
```

Repository search on the current default branch found no published:

```text
OD-2026-09-29-004
PASS_4_PLAN
```

Therefore Chat 6 should first reconcile its own orchestration state with the already-closed Round 3 before treating any later worker branch as an official next-round input.

## 4. Observed worker backlog after Round 3

The following branches exist in GitHub and are later than the certified Round-3 worker heads. They are observations only, not Chat-8 acceptance verdicts.

### Chat 1

Observed branch:

```text
chat-1/pass-4
HEAD = beed09508c8cba294b1e78d7b6b7f3226f72d734
```

Observed work includes immutable clean-reference recapture lineage.

However `chat_1_project_guided_capture/ORCHESTRATOR_HANDOFF.md` on that branch still identifies Pass 3 / `chat-1/pass-3`.

Status for central orchestration:

```text
IMPLEMENTATION EXISTS
CURRENT PASS-4 HANDOFF/FREEZE = NOT PROVEN
STAGE-1 READY = NO
```

### Chat 2

Observed cumulative branch:

```text
chat-2/pass-6
HEAD = 539d58567046fd29ccf2d42b629227ffe8da6546
```

Its handoff identifies Pass 6 and freezes the branch. The branch stack contains Pass 4 -> Pass 5 -> Pass 6 work, including:

- measurement-type unit semantics;
- unit-neutral uncertainty;
- canonical 1..3 anchor cardinality.

Draft PRs #29, #30 and #31 expose this stacked chain. Pass 4 was originally based on the Round-3 integration candidate, with Pass 5 and Pass 6 stacked on preceding worker heads.

Status for central orchestration:

```text
FROZEN WORKER INPUT EXISTS
ACCEPTED INTO NEXT CENTRAL ROUND = NO
CURRENT-MAIN BASELINE RECONCILIATION REQUIRED
```

### Chat 3

Observed cumulative branch:

```text
chat-3/pass-8
HEAD = d786e1d49b5c8f2837a3ce936f7f1c0d93336d49
```

Its Pass-8 handoff freezes the branch and documents residual-aware confidence for constraint promotion.

The same handoff explicitly records inherited shared-baseline drift: the worker ancestry still carries an obsolete Chat-6-owned Chat3->Chat4 integration-test lookup using `cad_verification_report["dimensions"]`, while current `main` uses canonical `items`.

Chat 3 correctly did not modify the shared test and requests replay of worker changes onto the corrected current shared baseline.

Status for central orchestration:

```text
FROZEN WORKER INPUT EXISTS
KNOWN SHARED-BASELINE DRIFT EXISTS
REPLAY/RECONCILIATION ON CURRENT MAIN REQUIRED
```

### Chat 4

Observed branch:

```text
chat-4/pass-7
HEAD = d9633e3b8e95158d359e502e9797d4876384cd09
```

Observed later work includes ANGLE vendor-dimension support and explicitly keeps real-host/C# production execution `UNVERIFIED`.

However `chat_4_cad_bridge_verification/ORCHESTRATOR_HANDOFF.md` on `chat-4/pass-7` still identifies the final Pass-3 handoff and Pass-3 branch.

Status for central orchestration:

```text
IMPLEMENTATION EXISTS
CURRENT PASS-7 HANDOFF/FREEZE = NOT PROVEN
STAGE-1 READY = NO
REAL HOST = UNVERIFIED
```

### Chat 5

Observed cumulative branch:

```text
chat-5/pass-8
HEAD = 82e2203aaeb69ee1fe9f89fd42d0aea451b8690f
```

Its Pass-8 handoff freezes the branch and documents deterministic snapshot-bound pagination over engineering knowledge queries.

The handoff also records that these later passes were continued by direct user instruction while no newer Chat-5-specific directive existed on `main`.

Status for central orchestration:

```text
FROZEN WORKER INPUT EXISTS
ACCEPTED INTO NEXT CENTRAL ROUND = NO
CURRENT-MAIN BASELINE RECONCILIATION REQUIRED
```

## 5. Unresolved risks

### R1 — central orchestration state lags worker development

Workers have accumulated later branch stacks while the accepted central state still publishes OD-003 / Pass-3 preparation metadata.

Risk:

- accidental integration of incompatible slices from different logical rounds;
- unclear acceptance boundary;
- a worker-local pass number being mistaken for a centrally accepted round number.

### R2 — not all later worker heads satisfy handoff/freeze protocol

At least Chat 1 Pass 4 and Chat 4 Pass 7 currently expose old Pass-3 handoff files.

They must not be treated as frozen Stage-1 inputs until Chat 6 obtains an exact current-pass handoff/freeze state.

### R3 — stacked worker ancestry contains old shared infrastructure

Chat 3 explicitly demonstrates this through the stale `dimensions` integration-test lookup inherited from older shared ancestry.

A future candidate must be assembled from the current accepted `main` shared baseline, importing only accepted worker-owned changes rather than blindly merging stale shared trees from worker branches.

### R4 — cross-slice semantics have advanced asynchronously

Later worker branches touch semantics that meet at boundaries:

- Chat 1: recapture/reference lineage;
- Chat 2: units, uncertainty and 1..3 anchors;
- Chat 3: constraints, satisfaction and residual-aware confidence;
- Chat 4: broader vendor entity/dimension support;
- Chat 5: normalized lifecycle/knowledge read models and pagination.

Even when each worker is locally correct, central acceptance requires proving that combinations remain truthful and fail closed across slice boundaries.

### R5 — real SOLIDWORKS remains the largest environment-only gap

Round 3 proved the generic/runtime-evidence software path, not a controlled real-host run.

The next central planning cycle should not allow later vendor features to accumulate into a false implication that the real COM/runtime gate has passed.

## 6. Architectural concerns for Chat 6

1. Preserve current `mrea.contracts.v1` as authoritative unless a concrete incompatibility produces a Change Request.
2. Do not import worker-owned copies of shared CI/integration tests when replaying later branches onto current `main`.
3. Keep physical measurement truth above inferred geometry/constraint confidence.
4. Keep raw `IMAGE_PX` measurement evidence in Chat 2 and normalization in Chat 3.
5. Keep final CAD verification semantics in the canonical/Primary path; vendor success alone is insufficient.
6. Keep lifecycle eligibility derived from verified CAD facts rather than worker/vendor claims.
7. Treat direct-user worker continuations as development backlog until they pass the normal Stage-1 -> Stage-2 -> Stage-3 chain.

## 7. Suggested priorities for next-pass planning

These are priorities for Chat 6 to consider, not a pre-authored Round-4 plan.

### Priority 0 — restore orchestration truth

Before reviewing later worker branches:

- update central orchestration state to record Round 3 as closed;
- establish the next directive/revision;
- define which exact worker heads constitute the next review set;
- define dependency/integration order.

### Priority 1 — obtain protocol-valid worker freeze points

Require current-pass handoff/freeze evidence where missing, especially:

- Chat 1 Pass 4;
- Chat 4 latest intended pass.

Do not infer readiness from implementation commits alone.

### Priority 2 — choose an explicit cut through stacked worker history

For Chat 2/3/5, later branches are cumulative stacks. Chat 6 should explicitly choose the accepted cut rather than assuming the highest pass number automatically belongs to one central round.

### Priority 3 — replay accepted worker-owned changes onto current main

Use final Round-3 `main` as the shared baseline and preserve current:

- canonical contracts;
- canonical fixtures;
- Chat-6-owned CI;
- corrected cross-slice integration tests.

Resolve worker ancestry drift by replay/reconciliation, not by reintroducing obsolete shared files.

### Priority 4 — strengthen the exact cross-slice gates affected by later work

High-value boundary cases to require during central review include:

```text
Chat 1 -> Chat 2
recaptured clean-reference lineage -> measurement evidence/reference provenance

Chat 2 -> Chat 3
1/2/3 raw IMAGE_PX anchors + mm/deg semantics + unit-neutral uncertainty -> geometry normalization

Chat 3 -> Chat 4
constraint promotion/confidence + canonical unresolved behavior -> generic/vendor CAD transfer without truth strengthening

Chat 4 -> Chat 5
verified/mismatch CAD facts -> lifecycle/manufacturing eligibility with no vendor-only shortcut
```

### Priority 5 — maintain a separate real-host track

Prepare an actual controlled Windows 11 x64 + SOLIDWORKS 2026 x64 execution path for:

- C# production build against installed official interops;
- COM startup/version validation;
- native `.SLDPRT` creation;
- read-back;
- artifact identity/hash;
- runtime evidence.

Until that run exists and passes:

```text
REAL_HOST = EXTERNAL_GATE_UNVERIFIED
```

## 8. Requested action from Chat 6

Chat 6 should use this document as an input to the next central planning cycle and produce the actual next-round directive/Stage-1 plan.

Chat 8 does not authorize integration of any Pass-4+ worker branch through this document.

Final handoff state:

```text
ROUND_3 = CLOSED
NEXT_ROUND_INPUT = READY_FOR_CHAT6
NEXT CENTRAL ROUND = NOT YET DESIGNED BY CHAT6
PASS-4+ WORKER BRANCHES = BACKLOG / PENDING FORMAL STAGE-1 SELECTION
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
```
