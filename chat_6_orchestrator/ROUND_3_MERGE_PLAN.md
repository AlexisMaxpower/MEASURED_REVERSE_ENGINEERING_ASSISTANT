# MREA — Round 3 Merge Plan

**Owner:** Chat 6 — Primary Orchestrator  
**Status:** `READY_FOR_DEPUTY1`  
**Stage:** handoff to Deputy 1; no final merge authority for Chat 6

## Stage-1 prerequisite status

The previous Chat-4 blocker is closed by `ROUND_3_STAGE1_CHAT4_REREVIEW_2026-09-30.md`.

Verified final worker set:

- Chat 1: `55918486d49a28ac85bf83a95e9917e40add79e2`
- Chat 2: `7311d95000d457e1010c95dbefe6ed0ad588203d`
- Chat 3: `08e716161a8c9173b7583d6ad87c84c10ddc4221`
- Chat 4: `08beb9c45cdc1bbbcdebe220059a64288a880095`
- Chat 5: `cdc5baceb281b657680d1e38cc49ea8094669ad8`

All five are `PROVISIONALLY_ACCEPTED` by Chat 6 Stage 1.

## Chat-4 correction evidence

Side Chat 4B:

- frozen head `9b37d023ea7b6355c752982e36b774c2fd96e358`
- `SOLIDWORKS_SIDE_HANDOFF.md` present
- exact FIX_REQUIRED delta contains the declared 13 side-owned files

Primary Chat 4:

- frozen head `08beb9c45cdc1bbbcdebe220059a64288a880095`
- genuine Pass-3 `ORCHESTRATOR_HANDOFF.md` present
- Side reconcile integrated without transferring final runtime-status authority to Side 4B
- final MREA CI run `36632747977` SUCCESS

Real Windows/SOLIDWORKS runtime remains `EXTERNAL_GATE_UNVERIFIED` / `REAL_HOST = UNVERIFIED` and must remain so until actual supported-host evidence exists.

## Shared baseline change during Stage 1

Chat 6 repaired the canonical Chat-3 -> Chat-4 integration test on `main` at:

`1a54ef40f84119d7482d971deb1e58749bf657b0`

Reason: Chat-6-owned test used stale `CADVerificationReport["dimensions"]`; canonical schema/code uses `items`.

Current `main` also contains Stage-1 orchestration records. Deputy 1 must start from the then-current `main`, not from the original Round-3 worker baseline.

## Review PRs

- #20 Chat 1
- #21 Chat 2
- #22 Chat 3
- #23 Chat 4
- #24 Chat 5

These are review inputs. Chat 6 does not merge them directly under the deputy-orchestrator protocol.

## Deputy 1 integration target

Deputy 1 should independently review Stage-1 findings and build:

`integration/pass-3-candidate`

from current accepted shared `main`.

Recommended logical integration order:

```text
Chat 1
  -> Chat 2
  -> Chat 3
  -> Chat 4
  -> Chat 5
```

The exact Git merge/cherry-pick strategy may be changed by Deputy 1 if conflict analysis shows a safer method, but the final candidate must explicitly record the exact accepted worker SHAs above.

## Required candidate gates

On `integration/pass-3-candidate`, require:

- canonical contracts/fixtures;
- Chat 1 tests;
- Chat 2 tests;
- Chat 3 tests;
- Chat 4 generic tests;
- Chat 5 tests;
- Integration Chat 1 -> Chat 2;
- Integration Chat 2 -> Chat 3;
- Integration Chat 3 -> Chat 4;
- Integration Chat 4 -> Chat 5.

Deputy 1 should additionally create/execute the most complete available golden software flow:

```text
Capture
-> Measurement
-> Geometry
-> generic CAD verification
-> Lifecycle
```

## Environment gate

Real Windows 11 + SOLIDWORKS 2026 COM execution may remain:

`EXTERNAL_GATE_UNVERIFIED`

It must not be converted to PASS by mocks, generic CAD tests, source presence, protocol-level evidence or synthetic runtime-input bundles.

## Pass-4 isolation

Branches `chat-3/pass-4`, `chat-4/pass-4`, `chat-4b/pass-4` and `chat-5/pass-4` already exist remotely, but the official shared `main` does not contain the next round directive at the Stage-1 handoff point.

Deputy 1 must **not** mix Pass-4 commits into the Round-3 integration candidate. Preserve them for later explicit orchestration.

## Handoff status

`ROUND_3_STAGE_1 = READY_FOR_DEPUTY1`

Deputy 1 now owns independent integration-candidate construction and verification. Round 3 is not closed until the remaining deputy stage(s) required by the protocol complete successfully.
