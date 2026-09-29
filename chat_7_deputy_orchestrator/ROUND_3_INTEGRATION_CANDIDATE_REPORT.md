# MREA — Round 3 Integration Candidate Report

**Owner:** Chat 7 — Deputy Orchestrator 1  
**Stage:** 2 — Technical Audit & Integration  
**Verdict:** `CANDIDATE_READY_FOR_FINAL_REVIEW`

## Integration candidate

**Branch:** `integration/pass-3-candidate`  
**Exact final candidate SHA:** `1c9ccb432664e57a24be8fe586bb07ad13fd5075`  
**Exact current main base:** `dcdb1b7a1399415522a1a17a7979dda536f116f4`  
**Candidate tree:** `435dda140d3980256ca32c42bd07d81b15c4328c`  
**Parent count:** 1  
**Parent:** current main `dcdb1b7a1399415522a1a17a7979dda536f116f4`

The candidate branch is intentionally frozen on the exact SHA above. Stage-2 documentation is stored on `chat-7/round-3-stage2-report` so documentation-only commits do not change the tested candidate SHA.

## Why this rebuild exists

Chat 8 Finding 002 required the Round-3 golden-path job to run on post-merge `main`, not only on the integration candidate.

Chat 6 changed `.github/workflows/ci.yml` on `main` at:

`dcdb1b7a1399415522a1a17a7979dda536f116f4`

so `Integration / Round 3 golden path` is now enabled for:

- `main`;
- integration-candidate pull requests;
- integration-candidate pushes.

The pre-merge `main` run `36643094207` then failed because pre-merge `main` does not yet contain `tests/integration/test_round3_golden_path.py` or the accepted Round-3 worker trees. No skip, placeholder, or weaker substitute was introduced.

This Stage-2 rebuild therefore verifies the corrected workflow on the actual accepted Round-3 candidate while preserving the final post-merge-main gate for Chat 8.

## Accepted frozen worker inputs

Only these previously accepted Round-3 worker heads are integrated:

| Slice | Frozen head | Integrated directory tree |
|---|---|---|
| Chat 1 | `55918486d49a28ac85bf83a95e9917e40add79e2` | `8c0be3cba0fbebc9505565c2d4cabfd216e802da` |
| Chat 2 | `7311d95000d457e1010c95dbefe6ed0ad588203d` | `9cf8811b8565b4101ea2ecf87657882e44543243` |
| Chat 3 | `08e716161a8c9173b7583d6ad87c84c10ddc4221` | `dee35a8f5d4781365b5613e8309ebb1f86f3d916` |
| Chat 4 | `08beb9c45cdc1bbbcdebe220059a64288a880095` | `c19331c4d91c8069e52e04a2a213e1f13d16dcdd` |
| Chat 5 | `cdc5baceb281b657680d1e38cc49ea8094669ad8` | `9e66264d5d19932883a34e753f320cefb8e76a8b` |

No frozen worker branch was reopened or changed. No Pass-4, Pass-5, or Pass-6 worker tree was integrated.

## Integration method

The new candidate was rebuilt directly from the current `main` tree rather than merging worker histories.

Method:

1. base tree: current `main` tree from `dcdb1b7a1399415522a1a17a7979dda536f116f4`;
2. replace only `chat_1_project_guided_capture/` through `chat_5_lifecycle_engineering_knowledge/` with the exact accepted Round-3 trees listed above;
3. preserve `tests/integration/test_round3_golden_path.py` exactly as blob `2e05dab6f2b82499b0bc23496a6e029d43d3e765`;
4. create one candidate commit with current `main` as its only parent;
5. update `integration/pass-3-candidate` to the exact resulting commit.

Candidate commit:

`1c9ccb432664e57a24be8fe586bb07ad13fd5075`

Candidate tree:

`435dda140d3980256ca32c42bd07d81b15c4328c`

Merge conflicts: **none**.  
Manual worker source-code conflict resolution: **none**.  
Canonical contract mutation by Chat 7: **none**.

## Preserved shared baseline

Because the current `main` is the direct parent, the candidate inherits the latest shared state, including:

- the Finding-002 CI correction enabling the golden job on `main`;
- Chat-8 Finding 002 documentation;
- canonical contracts and fixtures;
- shared integration tests;
- Chat-6 orchestration state.

## Candidate CI evidence

**Authoritative candidate run:** `36644505122`  
**Workflow:** `MREA CI`  
**Event:** `push`  
**Head SHA:** `1c9ccb432664e57a24be8fe586bb07ad13fd5075`  
**Status:** `completed`  
**Conclusion:** `success`

Actually executed and `SUCCESS`:

| Required job | Conclusion |
|---|---|
| Contracts / canonical fixtures | `SUCCESS` |
| Chat 1 / Capture | `SUCCESS` |
| Chat 2 / Measurement | `SUCCESS` |
| Chat 3 / Geometry | `SUCCESS` |
| Chat 4 / Generic CAD gate | `SUCCESS` |
| Chat 5 / Lifecycle | `SUCCESS` |
| Integration / Chat 1 -> Chat 2 | `SUCCESS` |
| Integration / Chat 2 -> Chat 3 | `SUCCESS` |
| Integration / Chat 3 -> Chat 4 | `SUCCESS` |
| Integration / Chat 4 -> Chat 5 | `SUCCESS` |
| Integration / Round 3 golden path | `SUCCESS` |

No mandatory boundary or golden-path gate is accepted as `skipped`.

The golden-path step `Run Round 3 Capture -> Physical Instance golden path` executed and completed `SUCCESS`.

## PR state

PR #27 targets `main` from `integration/pass-3-candidate`.

At the time of this report:

- base SHA: `dcdb1b7a1399415522a1a17a7979dda536f116f4`;
- head SHA: `1c9ccb432664e57a24be8fe586bb07ad13fd5075`;
- mergeable: `true`;
- merged: `false`.

Its description has been updated to the exact current candidate and CI evidence so it no longer advertises the superseded `199cf5a...` candidate.

## Finding 002 truth state

```text
FINDING_002_CI_DESIGN_CORRECTION = IMPLEMENTED
PRE_MERGE_MAIN_GOLDEN_RUN = EXECUTED_BUT_FAILED_TEST_FILE_ABSENT
REBUILT_CANDIDATE_FROM_CURRENT_MAIN = PASS
FOUR_BOUNDARY_GATES_ON_CANDIDATE = PASS
ROUND3_GOLDEN_ON_CANDIDATE = PASS
FULL_CANDIDATE_CI = PASS
FINAL_REVIEW = PENDING_CHAT_8
FINAL_MERGE = NOT_PERFORMED
POST_MERGE_MAIN_GOLDEN = NOT_YET_EXECUTED
ROUND_3 = NOT_CLOSED
```

Finding 002 is not declared closed by Chat 7. Chat 8 owns the protocol decision, final merge authorization, and the required post-merge `main` evidence.

## External gates

The following remain explicitly external/unverified:

- real Windows 11 x64 + SOLIDWORKS 2026 COM execution;
- production C#/.NET Framework build against installed official SOLIDWORKS interop assemblies;
- real native `.SLDPRT` generation/verification on a controlled SOLIDWORKS host.

Status:

`EXTERNAL_GATE_UNVERIFIED`

These are not represented as PASS by Linux CI or TestDouble CAD evidence.

## Handoff to Chat 8

```text
Round 3 Stage 2 verdict:
CANDIDATE_READY_FOR_FINAL_REVIEW

Candidate branch:
integration/pass-3-candidate

Exact tested candidate SHA:
1c9ccb432664e57a24be8fe586bb07ad13fd5075

Current main parent:
dcdb1b7a1399415522a1a17a7979dda536f116f4

Candidate CI run:
36644505122 — SUCCESS

Finding 002:
OPEN UNTIL CHAT 8 FINAL REVIEW + CERTIFIED MERGE + POST-MERGE MAIN GOLDEN SUCCESS

External gate:
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
```

Chat 7 does not merge the candidate into `main` and does not close Round 3.