# ROUND 3 — FINAL_REVIEW_FINDING 002

**Reviewer:** Chat 8 — Deputy Orchestrator 2 / Final Certifier  
**Owner:** Chat 6 — Primary Orchestrator / shared CI infrastructure  
**Severity:** BLOCKING / HIGH  
**Status:** OPEN  
**Detected:** 2026-09-30  
**Scope:** Stage 3 final review / post-merge CI completeness

## Verdict

`FIX_REQUIRED → Chat 6`

`DISAGREEMENT WITH STAGE 2`

Round 3 must **not** be merged or closed yet.

## What Stage 2 got right

The rebuilt candidate is technically coherent and its candidate CI is complete:

- candidate SHA: `199cf5a15a22a6b6a01b54540f5f856a18ca7752`;
- base main SHA: `b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`;
- candidate CI run: `36638965404` — `SUCCESS`;
- all five slice suites execute successfully;
- canonical contract fixtures execute successfully;
- all four cross-slice boundaries execute successfully;
- `Integration / Round 3 golden path` executes successfully;
- run attempt is `1`, so no rerun masks a first-attempt failure;
- real SOLIDWORKS remains correctly `EXTERNAL_GATE_UNVERIFIED`.

The problem is not candidate correctness. The problem is the **post-merge evidence path**.

## Problem

The current workflow runs the Round-3 golden path only when the ref starts with:

```text
refs/heads/integration/pass-
```

Therefore the same job is `skipped` on a push to `main`.

This has already been observed on corrected-main CI run `36638429445`:

- slice suites: `SUCCESS`;
- contracts: `SUCCESS`;
- all four boundaries: `SUCCESS`;
- `Integration / Round 3 golden path`: `SKIPPED`.

If Chat 8 merged candidate → main now, the required post-merge CI on the new main SHA would again skip the automatically executable golden path.

## Protocol conflict

`DEPUTY_ORCHESTRATORS_PROTOCOL.md` requires:

1. Chat 8 to verify candidate CI including the golden path;
2. a final golden path before round closure;
3. after merge, **full CI on the new main SHA**;
4. candidate-green alone is explicitly insufficient;
5. round closure only after final main CI is green.

The golden path is not an external/physical gate. It is an ordinary Linux/GitHub-hosted automated integration test and already passes on the candidate. Therefore it cannot be omitted from post-merge main CI under the `EXTERNAL_GATE_UNVERIFIED` exception.

## Stage-2 disagreement

Stage 2 treated the golden-path skip on corrected `main` as expected because the job was intentionally candidate-only.

Chat 8 does not accept that as sufficient final-release evidence. Candidate-only execution verifies the candidate SHA, but the protocol separately requires full CI on the **post-merge main SHA**.

This finding does not invalidate the Stage-2 worker audit, worker SHAs, candidate assembly, or candidate test result. It only blocks the final merge/closure path until post-merge CI can exercise the same golden software route.

## Required correction

Chat 6 must make the minimal shared-CI correction so that:

1. `Integration / Round 3 golden path` executes on `main` pushes as well as on `integration/pass-*-candidate`;
2. its dependency set remains at least: contracts + all five slices + all four boundaries;
3. worker-branch behavior is not broadened unnecessarily;
4. corrected `main` gets a full green CI run with the golden path actually executed, not skipped;
5. Chat 7 performs targeted re-audit of the CI correction;
6. because `main` changes, `integration/pass-3-candidate` is rebuilt/rebased from that corrected current main while preserving the accepted Round-3 worker trees;
7. the exact rebuilt candidate receives a complete green CI run;
8. Stage 2 updates its candidate report with the new base SHA, candidate SHA and run ID.

After those criteria are met, Chat 8 repeats Stage 3 final review.

## Non-scope

No Chat 1–5 worker branch should be reopened for this finding.

No canonical contract change is required.

No change to real-host truth is required:

```text
REAL_HOST = UNVERIFIED
EXTERNAL_GATE_UNVERIFIED
```

## Closure criteria

`FINAL_REVIEW_FINDING_002 = CLOSED` only after:

- golden path executes successfully on corrected `main`;
- Chat 7 re-audits the corrected CI design;
- candidate is rebuilt from that corrected main;
- full candidate CI is green on the exact final candidate SHA;
- post-merge workflow design guarantees that the golden path will execute on the final new main SHA.

Until then:

```text
ROUND 3 = NOT CLOSED
FINAL MERGE = BLOCKED
```
