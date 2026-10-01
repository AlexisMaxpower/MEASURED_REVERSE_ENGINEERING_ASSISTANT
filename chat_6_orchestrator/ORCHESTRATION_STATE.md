# MREA Orchestration State

**Control owner:** central orchestration  
**Finalizing role:** Orchestrator 2 / final orchestrator 2 of 2  
**Contract baseline:** `mrea.contracts.v1`  
**Status:** `ROUND_11_CLOSED_ACCEPTED_WITH_EXTERNAL_GATE`

## Round 11 accepted integration

The independently accepted Round-11 integration candidate was:

```text
branch: integration/pass-4-candidate
SHA:    f54d3841067e60e922340593b740f5a50fe4562f
tree:   38c951bec641c84f079f9247a64b7cd201210066
```

It was merged through PR #38. The merge commit was:

```text
7c03295200f72dbe6aa9c79bd21113c9f2df87e3
```

Round-11 worker inputs independently audited before merge:

```text
Chat 2  chat-2/pass-11-verification @ f8692b91e6a2eb867d8f6b714b97e05f7477a100
Chat 3  chat-3/pass-11              @ ffd2fd71e325da690fccebbfa1c1ce904571f655
Chat 4  chat-4/pass-11              @ 09a0fef643ebf6173c82af42de7b86ec7c2e0b53
Chat 5  chat-5/pass-11              @ fe6038bd6f709d38c299b36b979ead78a86d8734
```

Chat 2 and Chat 3 Pass-11 tops were verification/documentation-only. Chat 4 and Chat 5 accepted product-owned surfaces were replayed into the central candidate without importing obsolete shared/control history.

## Candidate CI evidence

Exact candidate `f54d3841067e60e922340593b740f5a50fe4562f` passed both central suites:

```text
36798866892  MREA CI                SUCCESS
36798866917  MREA Round 4 Truth CI  SUCCESS
```

All mandatory slice, contract, boundary and golden-path jobs actually executed; no mandatory gate was accepted through `skipped` or `cancelled` status.

## Final post-merge finding and correction

The first post-merge Truth run on merge commit `7c03295200f72dbe6aa9c79bd21113c9f2df87e3` exposed a shared workflow defect:

```text
36800154366  MREA Round 4 Truth CI
```

The shared infrastructure job executed, but all four truth boundaries and the Round-4 golden path were skipped because their job-level conditions only admitted `integration/pass-4-candidate`.

Final Orchestrator 2 corrected `.github/workflows/round4_truth.yml` so the mandatory truth jobs also execute on `refs/heads/main`.

Correction commit / certified software+CI baseline:

```text
c35c2abc08798f1da4083d1a33dbaa1f42db3af9
```

Exact-main evidence after the correction:

```text
36800327016  MREA CI                SUCCESS
36800327069  MREA Round 4 Truth CI  SUCCESS
```

For `36800327016`, contracts, all five slices, all four normal integration boundaries and the normal golden path executed successfully.

For `36800327069`, the shared gate, all four Round-4 truth boundaries and the Round-4 golden path executed successfully. No required truth gate was skipped.

## Resolved legacy blockers

The old Round-4 Chat-3 uncertainty-propagation blocker and Chat-5 runtime-evidence blocker are closed in the integrated repository. The historical `FIX_REQUIRED / REOPENED` state is no longer current authority.

```text
OPEN_SOFTWARE_BLOCKERS = NONE
CURRENT_CANDIDATE_ACCEPTED = TRUE
MERGE_TO_MAIN_COMPLETED = TRUE
ROUND_11_CLOSED = TRUE
NEXT_FULL_WORKER_PASS = READY
```

No worker is currently reopened by the old Round-4 findings. A new worker pass must start from the current shared `main` under a new/current orchestration directive rather than from historical frozen baselines.

## External environment truth

Generic Linux CI, test doubles and synthetic runtime evidence do not promote the real SOLIDWORKS host state.

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

Therefore the final Round-11 disposition is:

```text
ROUND 11 CLOSED — ACCEPTED_WITH_EXTERNAL_GATE
```
