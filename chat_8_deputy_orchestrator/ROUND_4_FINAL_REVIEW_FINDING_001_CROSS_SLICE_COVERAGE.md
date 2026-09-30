# ROUND 4 — FINAL_REVIEW_FINDING 001

**Reviewer:** Chat 8 — Deputy Orchestrator 2 / Final Certifier  
**Owner:** Chat 6 — Primary Orchestrator / shared integration tests and CI  
**Severity:** BLOCKING / HIGH  
**Status:** OPEN  
**Detected:** 2026-09-30  
**Candidate under review:** `36a17aa8fecbf532f33f059b776a63050df185f7`  
**Frozen base:** `968863a9823e8ce993c08d902be2d83dabfb78e6`

## Problem

Round 4 is defined by `PASS_4_PLAN_2026-09-30.md` as **Backlog Reconciliation & Cross-Slice Truth Hardening** and explicitly requires additional cross-slice cases for the selected backlog plus a Round-4 golden path at Stage 2.

The final candidate does not contain Round-4-specific shared integration coverage. Its protected root `tests/integration/` tree remains the pre-existing Round-3 integration suite and contains only:

- `test_chat1_to_chat2_boundary.py`;
- `test_chat2_to_chat3_boundary.py`;
- `test_chat3_to_chat4_boundary.py`;
- `test_chat4_to_chat5_boundary.py`;
- `test_round3_golden_path.py`.

The shared workflow likewise runs `Integration / Round 3 golden path` by executing `tests/integration/test_round3_golden_path.py`.

Running the old tests against a Round-4 composition is useful regression evidence, but it does not prove the new Round-4 cross-slice truth-hardening requirements.

## Missing Round-4 evidence

### Chat 1 -> Chat 2

OD-004 requires recaptured clean-reference lineage to reach measurement evidence/reference provenance, no silent binding to superseded reference context, and no mutation of verified physical facts. The current shared boundary creates one clean reference and never recaptures/supersedes it.

### Chat 2 -> Chat 3

OD-004 requires 1/2/3 raw `IMAGE_PX` anchors, mm/deg semantics, unit-neutral uncertainty, and downstream support or explicit fail-closed rejection. The current shared boundary exercises one two-anchor `LINEAR_EXTERNAL` mm measurement only.

### Chat 3 -> Chat 4

OD-004 requires constraint candidate -> satisfaction/residual confidence -> canonical constraint or explicit unresolved -> CAD, without strengthening physical truth or inventing relations. The current shared boundary uses deterministic LINE/CIRCLE primitives and does not exercise the new constraint-resolution/residual path.

### Chat 4 -> Chat 5

OD-004 requires `VERIFIED/MISMATCH/UNVERIFIED` CAD evidence through manufacturing eligibility/lifecycle facts and prevents later knowledge/read-model layers from reinterpreting failed CAD evidence as eligible. The current shared boundary covers VERIFIED and generic FAILED manufacturing eligibility but not Round-4 runtime `UNVERIFIED` semantics through later persistence/read-model/knowledge layers.

## Evidence already verified by Chat 8

Candidate provenance itself is clean:

- exact candidate `36a17aa8fecbf532f33f059b776a63050df185f7`;
- exact frozen base `968863a9823e8ce993c08d902be2d83dabfb78e6`;
- merge base equals frozen base;
- candidate is one commit ahead and zero behind;
- replayed worker-owned surfaces match the Round-4 replay manifest;
- shared/protected `.github`, `core`, root `tests`, Chat-6 and Chat-8 trees are preserved;
- PR run `36738869778` is green and all 11 configured jobs actually executed.

Worker-local tests also show the new mechanisms exist and pass inside their owning slices. This finding is therefore not a worker implementation rejection. It is a missing shared cross-slice evidence gate.

## Why this is blocking

Round 4's explicit purpose is to prove that advanced slice semantics compose correctly across ownership boundaries. A green run of unchanged Round-3 boundaries and the Round-3 golden path cannot establish that requirement.

Accepting the candidate now would make the Stage-2 verification stronger than the available evidence supports.

## Required correction

Chat 6 owns the correction because root integration tests and shared CI are Chat-6-owned infrastructure.

1. Add shared Round-4 integration coverage for the selected OD-004 cross-slice truth-hardening cases.
2. Add an explicit Round-4 golden-path gate (`test_round4_golden_path.py` is the clearest form; equivalent repository-owned tests are acceptable only if they demonstrably cover the same semantics).
3. Ensure CI executes the new Round-4 gate on `integration/pass-4-candidate`, not merely `test_round3_golden_path.py`.
4. Run corrected `main` CI and record exact SHA/run.
5. Rebuild/replay the Round-4 candidate from the corrected frozen `main`, preserving the accepted worker replay manifest unless a new test exposes an actual worker defect.
6. Obtain full candidate CI with contracts, all five slices, all four boundaries, and Round-4 truth-hardening/golden-path gates executed + SUCCESS.
7. Return the exact replacement candidate SHA to Chat 8 for repeated Final Review.

Worker branches Chat 1–5 must not be reopened merely to fix this shared-test gap. Route only concrete worker defects if the new integration tests expose one.

## External gate

This finding does not alter:

```text
REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED
PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED
NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED
```

## Final Review status

```text
FINAL_REVIEW_FIX_REQUIRED
MERGE_TO_MAIN = NOT_AUTHORIZED
ROUND_4 = NOT_CLOSED
```
