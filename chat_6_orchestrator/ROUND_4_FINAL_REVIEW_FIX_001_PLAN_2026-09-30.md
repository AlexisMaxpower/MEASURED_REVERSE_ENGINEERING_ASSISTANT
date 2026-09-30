# Round 4 Final Review Fix 001 — Cross-Slice Truth Coverage

**Owner:** Chat 6 — Orchestrator / Repository Integrator  
**Source finding:** `chat_8_deputy_orchestrator/ROUND_4_FINAL_REVIEW_FINDING_001_CROSS_SLICE_COVERAGE.md`  
**Status:** FIX IN PROGRESS  
**Round:** 4

## Finding accepted

Chat 8 correctly identified that the green candidate only proved Round-3 regression compatibility. `PASS_4_PLAN_2026-09-30.md` requires new Round-4 cross-slice truth-hardening evidence and a Round-4 golden path.

This correction is owned by Chat 6 because root integration tests and shared CI are orchestrator-owned infrastructure.

## Shared gates added

The correction adds a separate companion workflow:

`.github/workflows/round4_truth.yml`

The existing `.github/workflows/ci.yml` remains the Round-3 regression suite. The companion workflow adds explicit Round-4 evidence without weakening or replacing existing regression gates.

New shared tests:

- `tests/integration/test_round4_chat1_to_chat2_truth.py`
- `tests/integration/test_round4_chat2_to_chat3_truth.py`
- `tests/integration/test_round4_chat3_to_chat4_truth.py`
- `tests/integration/test_round4_chat4_to_chat5_truth.py`
- `tests/integration/test_round4_golden_path.py`

## Main-vs-candidate execution policy

The corrected `main` does not yet contain the accepted worker replay, so the semantic Round-4 jobs cannot truthfully execute there before the candidate is rebuilt.

Therefore on corrected `main` the companion workflow executes a shared-gate infrastructure job that compiles all new repository-owned tests. The full Round-4 semantic jobs run on the official `integration/pass-4-candidate` after the accepted Chat 1–5 worker replay is reapplied onto the corrected frozen `main`.

Final candidate acceptance requires both:

1. existing `MREA CI` regression suite green; and
2. `MREA Round 4 Truth CI` with all four Round-4 boundaries plus Round-4 golden path actually executed and green.

## Assertions by boundary

### Chat 1 -> Chat 2

- create real clean-reference attempt v1 and measurement evidence;
- create and verify a Chat-2 physical measurement against v1;
- recapture clean reference as v2 with explicit supersession;
- canonical CapturePackage exposes the active attempt only;
- stale v1 Chat-2 evidence fails closed against v2 instead of silently rebinding;
- the previously verified physical fact remains immutable;
- a new explicit v2 measurement succeeds.

### Chat 2 -> Chat 3

- real Chat-2 1-anchor, 2-anchor and 3-anchor measurements;
- raw anchors remain `IMAGE_PX` at Chat 2;
- length/depth remain `mm`, ANGLE remains `deg`;
- Chat 3 owns normalization to `MAT_XY_MM`;
- anchor cardinality and unit semantics survive normalization/binding;
- unit-neutral physical uncertainty must be preserved downstream or explicitly rejected, never silently erased.

### Chat 3 -> Chat 4

- constraint candidate is evaluated through satisfaction/residual confidence;
- a safe relation is promoted and reaches Chat 4 unchanged;
- a low-confidence residual relation becomes explicit unresolved evidence;
- Chat 4 preserves canonical constraint/unresolved facts and does not invent relations.

### Chat 4 -> Chat 5

- synthetic `SOLIDWORKS_2026` identity is deliberately not real-host evidence;
- numerical CAD verification may be `VERIFIED` while runtime status is `UNVERIFIED`;
- Chat 5 must consume and persist that runtime state for runtime-gated CAD origins;
- manufacturing remains fail-closed for runtime `UNVERIFIED` and numerical mismatch;
- persistence/read-model reopening must not reinterpret blocked CAD evidence as eligible.

This synthetic CI evidence MUST NOT promote the external real SOLIDWORKS gate.

## Round-4 golden path

The new golden path composes:

recapture lineage -> active measurement evidence -> 3-anchor ANGLE in degrees with uncertainty -> geometry normalization/binding -> residual-aware constraint resolution -> generic CAD verification -> lifecycle manufacturing/physical instance.

The separate Chat4->Chat5 runtime gate covers the negative vendor/runtime path so the golden path does not fake controlled-host execution.

## Worker defect routing policy

These tests are evidence gates, not acceptance theatre.

If the rebuilt candidate fails because a selected worker implementation cannot satisfy the Round-4 semantics, Chat 6 will NOT weaken the test merely to obtain green CI. A concrete `FIX_REQUIRED` will be routed to the owning worker, with the failed shared gate as evidence.

No shared canonical contract change is pre-approved by this fix.

## External gate unchanged

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Closure condition

`FINAL_REVIEW_FINDING_001` can be returned to Chat 8 only after:

1. corrected shared infrastructure is committed and green on `main` for the tests it can execute there;
2. candidate is rebuilt from that exact frozen `main` using the accepted replay manifest;
3. existing MREA CI is green on exact candidate;
4. all four Round-4 truth boundaries and the Round-4 golden path actually execute and succeed on exact candidate;
5. any concrete worker defect exposed by those gates is fixed by its owner and independently replayed/reverified.
