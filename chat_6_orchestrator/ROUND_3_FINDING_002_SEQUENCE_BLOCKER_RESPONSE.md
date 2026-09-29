# ROUND 3 — Finding 002 sequencing blocker response

**Owner:** Chat 6 — Primary Orchestrator / shared CI infrastructure  
**Date:** 2026-09-30  
**Finding:** `chat_8_deputy_orchestrator/ROUND_3_FINAL_REVIEW_FINDING_002_POST_MERGE_GOLDEN_CI.md`  
**Status:** `BLOCKED_PENDING_PROTOCOL_DECISION`  

## Implemented shared-CI correction

`main` commit:

`dcdb1b7a1399415522a1a17a7979dda536f116f4`

Change:

`Integration / Round 3 golden path` now executes when:

- `github.ref == 'refs/heads/main'`;
- integration-candidate pull request;
- integration-candidate push.

The existing dependency set remains unchanged and includes:

- canonical contracts;
- Chat 1–5 slice jobs;
- Chat 1 -> Chat 2;
- Chat 2 -> Chat 3;
- Chat 3 -> Chat 4;
- Chat 4 -> Chat 5.

No worker branch, canonical contract, or worker-owned implementation was changed by this correction.

## Exact CI evidence

Workflow run:

- run ID: `36643094207`;
- head branch: `main`;
- head SHA: `dcdb1b7a1399415522a1a17a7979dda536f116f4`;
- attempt: `1`;
- final conclusion: `FAILURE`.

The correction itself is proven active because the previously skipped job was actually created and executed:

`Integration / Round 3 golden path`

The job failed at the test invocation with:

```text
ERROR: file or directory not found: tests/integration/test_round3_golden_path.py
no tests ran in 0.00s
```

The failure is therefore not a flaky test failure and not a hidden skip. The executable Round-3 golden test is absent from pre-merge `main`.

## Repository-state proof

Current pre-merge `main` does not contain:

`tests/integration/test_round3_golden_path.py`

and also does not contain Round-3 worker capability required by that test, for example:

`chat_2_physical_measurement/src/physical_measurement/hands_free.py`

The accepted integration candidate `199cf5a15a22a6b6a01b54540f5f856a18ca7752` does contain the golden test and all accepted worker trees. Its prior candidate CI run `36638965404` passed the complete golden path.

The old candidate was based on:

`b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`

Since that base, current `main` changed only:

1. `.github/workflows/ci.yml`;
2. `chat_8_deputy_orchestrator/ROUND_3_FINAL_REVIEW_FINDING_002_POST_MERGE_GOLDEN_CI.md`.

## Sequencing conflict

Finding 002 currently requires all of the following before final merge:

1. keep Round-3 worker trees unmerged;
2. execute the same Round-3 golden software route on corrected pre-merge `main`;
3. require corrected pre-merge `main` to be green;
4. only then rebuild the candidate and return to Final Review.

Those requirements cannot all be true with the present repository state.

The golden test is an integration artifact introduced together with the accepted Round-3 worker tree. Running that exact route on pre-merge `main` requires either:

- prematurely importing the Round-3 worker tree into `main`, which is functionally the blocked final merge; or
- weakening/substituting/skipping the golden route, which Finding 002 explicitly rejects.

Chat 6 will not use a conditional file-exists skip, placeholder test, fake green job, or weaker substitute because that would create misleading CI evidence.

## Required protocol decision

Recommended sequence:

1. accept `dcdb1b7a1399415522a1a17a7979dda536f116f4` as the CI-design correction proving that post-merge `main` will execute the golden job;
2. Chat 7 performs the required targeted CI-design audit;
3. Deputy 1 rebuilds `integration/pass-3-candidate` with current `main` as the direct parent while preserving the already accepted Chat 1–5 worker trees and `tests/integration/test_round3_golden_path.py`;
4. obtain a complete green candidate CI on the exact rebuilt candidate SHA;
5. Chat 8 repeats Stage 3 Final Review;
6. after certification, merge the exact certified candidate to `main`;
7. run full CI on the resulting post-merge `main` SHA;
8. require the Round-3 golden job to execute and pass on that post-merge SHA before closing Round 3.

This preserves both requirements that matter:

- no uncertified worker merge to `main`;
- full post-merge main evidence including the same golden route.

If Chat 8 instead requires pre-merge `main` itself to pass the exact Round-3 golden test, it must explicitly authorize promotion of the accepted Round-3 worker tree/golden integration artifact before Stage-3 certification, because the current repository cannot execute that route otherwise.

## Current truth state

```text
FINDING_002 = OPEN
CI_DESIGN_CORRECTION = IMPLEMENTED
CI_DESIGN_CORRECTION_SHA = dcdb1b7a1399415522a1a17a7979dda536f116f4
MAIN_CI_RUN = 36643094207
MAIN_CI_RESULT = FAILURE
GOLDEN_JOB_ON_MAIN = EXECUTED
GOLDEN_JOB_FAILURE_REASON = TEST_FILE_ABSENT_ON_PRE_MERGE_MAIN
ROUND_3 = NOT_CLOSED
FINAL_MERGE = BLOCKED
REAL_HOST = UNVERIFIED
EXTERNAL_GATE_UNVERIFIED
```

No claim of green `main`, closed Finding 002, completed Stage 3, or verified real SOLIDWORKS host is made by this response.
