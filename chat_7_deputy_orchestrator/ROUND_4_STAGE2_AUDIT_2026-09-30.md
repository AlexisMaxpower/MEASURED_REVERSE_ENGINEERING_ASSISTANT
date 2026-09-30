# MREA — Round 4 Stage 2 Audit

**Owner:** Chat 7 — Deputy Orchestrator 1 / Independent Integration Auditor  
**Date:** 2026-09-30  
**Status:** `CANDIDATE_READY_FOR_FINAL_REVIEW`

## 1. Stage-2 input

Stage 2 was started only after Chat 6 published the completed Round-4 Stage-1 package on `main`.

Authoritative Stage-1 base used for the final candidate:

- `main`: `11975decc69caf80952942c58377f9d896d70303`;
- tree: `dab23980235788019477fea6cd5bfbd9d1dda29a`;
- Stage-1 review: `chat_6_orchestrator/ROUND_4_STAGE1_FINAL_REVIEW_2026-09-30.md`;
- replay manifest: `chat_6_orchestrator/ROUND_4_REPLAY_MANIFEST_2026-09-30.md`.

Selected frozen worker inputs recorded by Stage 1:

- Chat 1: `chat-1/pass-4` @ `a7d607f8cdd281749ae40529de15c2d84dfda78e`;
- Chat 2: `chat-2/pass-6` @ `539d58567046fd29ccf2d42b629227ffe8da6546`;
- Chat 3: `chat-3/pass-8` @ `d786e1d49b5c8f2837a3ce936f7f1c0d93336d49`;
- Chat 4: `chat-4/pass-7` @ `61f37a4dd46921b7fe9145bcbe5242bc3f6417b3`;
- Chat 5: `chat-5/pass-8` @ `82e2203aaeb69ee1fe9f89fd42d0aea451b8690f`.

## 2. Candidate rebuild history

An initial Stage-2 candidate was built at:

`ec75cba2b19fdfc0a26fd3fda0b090a1c95bbb84`

That candidate passed CI, but before Final Review handoff an independent re-check detected that `main` had advanced from `739bf696e774eb9a02cd13cda8c32818d572d4f8` to `11975decc69caf80952942c58377f9d896d70303`.

The intervening main commit changed only:

`chat_6_orchestrator/SLICE_STATUS.md`

The initial candidate was therefore marked **SUPERSEDED** rather than handed to Chat 8.

Because no PR had yet been opened and Final Review had not begun, the official branch was rebuilt from the latest exact `main` and re-tested. No CI result from the superseded SHA is used as evidence for the final candidate.

## 3. Exact final candidate

```text
branch = integration/pass-4-candidate
base/main = 11975decc69caf80952942c58377f9d896d70303
candidate = 05f999e1cc24307cfb4842d19bc5d42a1f1c9721
candidate_tree = fa751dce49166023741324c338f1dd587b24cc49
parent = 11975decc69caf80952942c58377f9d896d70303
```

Git comparison confirms:

```text
candidate vs base = ahead by 1
candidate vs base = behind by 0
merge base = exact current base main
```

## 4. Replay/provenance method

The candidate was constructed with GitHub Git Data objects from the exact Stage-1 replay manifest.

Only Chat-6-approved worker-owned replay surfaces were overlaid onto current `main`.

Preserved from current `main`:

- `.github/workflows/**`;
- `core/contracts/**`;
- canonical contract fixtures;
- shared `tests/integration/**`;
- Chat-6-owned active `ORCHESTRATOR_DIRECTIVE.md` files;
- worker `ORCHESTRATOR_HANDOFF.md` control/freeze records;
- Chat-6 orchestration state and review files, including the latest `SLICE_STATUS.md`.

No blind worker-history merge was used. No whole worker directory was replaced.

The base-to-candidate compare shows worker-owned implementation/test/docs surfaces only for the five selected slices.

## 5. Exact final candidate CI

Authoritative workflow run:

```text
MREA CI = 36728546973
head_sha = 05f999e1cc24307cfb4842d19bc5d42a1f1c9721
status = completed
conclusion = success
```

All 11 mandatory jobs completed with `success`:

1. `Contracts / canonical fixtures`;
2. `Chat 1 / Capture`;
3. `Chat 2 / Measurement`;
4. `Chat 3 / Geometry`;
5. `Chat 4 / Generic CAD gate`;
6. `Chat 5 / Lifecycle`;
7. `Integration / Chat 1 -> Chat 2`;
8. `Integration / Chat 2 -> Chat 3`;
9. `Integration / Chat 3 -> Chat 4`;
10. `Integration / Chat 4 -> Chat 5`;
11. `Integration / Round 3 golden path`.

No mandatory job is accepted through `skipped`.

The golden job actually executed the step:

`Run Round 3 Capture -> Physical Instance golden path`

and that step completed `success`.

The historical job name still says `Round 3 golden path`; Stage 2 treats the actual current candidate execution, not the label text, as evidence. The test itself executed on the exact Round-4 candidate SHA.

## 6. High-risk findings

### Shared-baseline drift

Chat 3's earlier worker red run was caused by stale shared ancestry using `cad_verification_report["dimensions"]` instead of current canonical `items`.

The final candidate is built from current `main`, so the stale shared integration test was not imported. On the final candidate, `Integration / Chat 3 -> Chat 4` is `success`.

### Measurement/geometry truth

The candidate preserves the architecture where raw measurement anchors remain upstream evidence and geometry/constraint logic cannot silently strengthen verified physical measurements.

### CAD/lifecycle truth

Generic CAD verification and downstream lifecycle remain separately gated. Vendor worker success is not manufacturing authorization by itself.

### SOLIDWORKS external gate

```text
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION C#/.NET FRAMEWORK BUILD ON CONTROLLED HOST = UNVERIFIED
NATIVE .SLDPRT GENERATION + READ-BACK = UNVERIFIED
```

Linux/TestDouble/generic CAD CI is not represented as real-host evidence.

## 7. Pull request

Draft PR:

`#38 — Round 4 — Deputy 1 integration candidate`

Expected immutable review target:

```text
base = main @ 11975decc69caf80952942c58377f9d896d70303
head = integration/pass-4-candidate @ 05f999e1cc24307cfb4842d19bc5d42a1f1c9721
```

The PR must not be merged before Chat 8 independently rechecks the exact head/base relationship and candidate CI.

## 8. Stage-2 verdict

```text
STAGE_2 = ACCEPTED
CANDIDATE_PROVENANCE = PASS
CURRENT_MAIN_BASE = PASS
FILE_LEVEL_REPLAY_DISCIPLINE = PASS
CANONICAL_CONTRACT_PRESERVATION = PASS
FIVE_SLICE_CI = PASS
FOUR_BOUNDARY_CI = PASS
GOLDEN_PATH = PASS
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED

EXACT_CANDIDATE_FOR_FINAL_REVIEW = 05f999e1cc24307cfb4842d19bc5d42a1f1c9721
CANDIDATE_TREE = fa751dce49166023741324c338f1dd587b24cc49
PR = 38
FINAL_MERGE_AUTHORIZATION = PENDING_CHAT8
```

Chat 7 does not merge the candidate and does not close Round 4.