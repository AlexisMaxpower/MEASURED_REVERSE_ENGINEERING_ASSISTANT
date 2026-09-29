# MREA — Round 3 Merge Plan

**Owner:** Chat 6 — Primary Orchestrator  
**Status:** `BLOCKED_PENDING_CHAT4_FIX`  
**Stage:** preparation for Deputy 1, no final merge authority

## Preconditions

This plan is not executable until Chat 4 becomes `PROVISIONALLY_ACCEPTED`.

Required first:

1. `chat-4b/pass-3` contains the assigned host-readiness implementation.
2. `chat_4_cad_bridge_verification/SOLIDWORKS_SIDE_HANDOFF.md` exists remotely.
3. Primary `chat-4/pass-3` reconciles the side result.
4. Primary `ORCHESTRATOR_HANDOFF.md` is updated to a real Pass-3 handoff.
5. Refreshed Chat-4 review CI is green against current shared baseline.
6. Chat 6 performs targeted re-review and publishes `READY_FOR_DEPUTY1`.

## Frozen worker candidates currently preserved

- Chat 1: `55918486d49a28ac85bf83a95e9917e40add79e2`
- Chat 2: `7311d95000d457e1010c95dbefe6ed0ad588203d`
- Chat 3: `08e716161a8c9173b7583d6ad87c84c10ddc4221`
- Chat 4: pending corrected final head after FIX_REQUIRED
- Chat 5: `cdc5baceb281b657680d1e38cc49ea8094669ad8`

## Shared baseline change during Stage 1

Chat 6 repaired the canonical integration test on `main`:

`1a54ef40f84119d7482d971deb1e58749bf657b0`

Reason: Chat-6-owned test used stale `CADVerificationReport["dimensions"]`; canonical schema/code uses `items`.

This emergency shared repair invalidated stale PR evidence, so all worker review PRs were reopened/created against the corrected baseline and rerun.

## Draft review PRs

- #20 Chat 1
- #21 Chat 2
- #22 Chat 3
- #23 Chat 4 primary — currently partial/FIX_REQUIRED
- #24 Chat 5

Chat 6 must not merge these into `main` under the deputy-orchestrator protocol.

## Recommended Deputy 1 integration strategy

After Chat 4 is corrected, Chat 7 should independently review Stage 1 findings and build:

`integration/pass-3-candidate`

from the then-current accepted shared `main`.

Recommended logical integration order:

```text
Chat 1
  -> Chat 2
  -> Chat 3
  -> Chat 4
  -> Chat 5
```

The exact Git merge order may be changed by Chat 7 if dependency/conflict analysis shows a safer order, but all five accepted worker SHAs must be explicitly recorded.

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

Chat 7 should additionally create/execute the most complete available golden software flow:

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

It must not be converted to PASS by mocks, generic CAD tests, source presence or protocol-level evidence.

## Handoff to Deputy 1

Chat 6 must not issue the Deputy-1 handoff while Chat 4 remains `FIX_REQUIRED`.

Once corrected, Chat 6 will append a targeted review result identifying the exact final Chat-4 head and CI run, then mark Stage 1:

`READY_FOR_DEPUTY1`
