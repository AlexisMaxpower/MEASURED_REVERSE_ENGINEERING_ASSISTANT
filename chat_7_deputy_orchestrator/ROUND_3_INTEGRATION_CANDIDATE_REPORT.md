# MREA — Round 3 Integration Candidate Report

**Owner:** Chat 7 — Deputy Orchestrator 1  
**Stage:** 2 — Technical Audit & Integration  
**Verdict:** `CANDIDATE_READY_FOR_FINAL_REVIEW`

## Integration candidate

**Branch:** `integration/pass-3-candidate`  
**Exact final candidate SHA:** `199cf5a15a22a6b6a01b54540f5f856a18ca7752`  
**Exact corrected main base:** `b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`  
**Candidate tree:** `7aa08438de7a3f0b57acef62b9654c079bb3dfa3`  
**Parent count:** 1  
**Parent:** corrected main `b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`

The candidate branch is intentionally frozen on the exact SHA above. Stage-2 documentation is stored on `chat-7/round-3-stage2-report` so documentation-only commits do not change the tested candidate SHA.

## Accepted frozen worker inputs

Only these previously accepted Round-3 worker heads were integrated:

| Slice | Frozen head | Integrated directory tree |
|---|---|---|
| Chat 1 | `55918486d49a28ac85bf83a95e9917e40add79e2` | `8c0be3cba0fbebc9505565c2d4cabfd216e802da` |
| Chat 2 | `7311d95000d457e1010c95dbefe6ed0ad588203d` | `9cf8811b8565b4101ea2ecf87657882e44543243` |
| Chat 3 | `08e716161a8c9173b7583d6ad87c84c10ddc4221` | `dee35a8f5d4781365b5613e8309ebb1f86f3d916` |
| Chat 4 | `08beb9c45cdc1bbbcdebe220059a64288a880095` | `c19331c4d91c8069e52e04a2a213e1f13d16dcdd` |
| Chat 5 | `cdc5baceb281b657680d1e38cc49ea8094669ad8` | `9e66264d5d19932883a34e753f320cefb8e76a8b` |

No frozen worker branch was reopened or changed. No Pass-4 or Pass-5 branch content was integrated.

## Shared baseline retained from corrected main

The candidate retains shared repository state from exact main `b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`, including:

- corrected `.github/workflows/ci.yml` candidate trigger and boundary conditions;
- canonical contracts;
- canonical fixtures;
- shared boundary integration tests;
- Chat-6 orchestration records;
- Chat-8 `FINAL_REVIEW_FINDING_001` record.

The candidate does not import shared files from worker histories.

## Preserved golden path

`tests/integration/test_round3_golden_path.py` is preserved from the previous candidate exactly as blob:

`2e05dab6f2b82499b0bc23496a6e029d43d3e765`

It exercises the available automated Round-3 route:

```text
Capture
  -> canonical CapturePackage
Measurement
  -> voice-reported candidate + explicit user confirmation
  -> canonical MeasurementPackage
Geometry
  -> IMAGE_PX -> MAT_XY_MM normalization + measurement binding
  -> canonical SketchPackage
CAD
  -> generic transfer/read-back verification
  -> CADPackage + VERIFIED CADVerificationReport
Lifecycle
  -> CAD revision -> manufacturing -> PhysicalPartInstance
```

It deliberately does not claim real SOLIDWORKS COM execution.

## Integration method and conflicts

Integration was performed as a clean tree rebuild from corrected main rather than by merging historical worker branches.

Method:

1. start from corrected main tree `b55a540d67208fdf933fff0620d3fa394f9a4c5d`;
2. replace only each worker-owned slice directory with the exact tree from its frozen Round-3 head;
3. add the preserved golden-path blob;
4. create one candidate commit with corrected main as its only parent;
5. force-update `integration/pass-3-candidate` to the resulting exact commit.

Merge conflicts: **none**.  
Manual source-code conflict resolution: **none**.  
Canonical contract mutation by Chat 7: **none**.

## Corrected main CI evidence

Corrected main:

- SHA: `b78eb3f7d8295ca7693cbc6cf060c1474b0ea050`;
- MREA CI run: `36638429445`;
- conclusion: `SUCCESS`.

Actually executed + SUCCESS on corrected main:

- Contracts / canonical fixtures;
- Chat 1 / Capture;
- Chat 2 / Measurement;
- Chat 3 / Geometry;
- Chat 4 / Generic CAD gate;
- Chat 5 / Lifecycle;
- Integration / Chat 1 -> Chat 2;
- Integration / Chat 2 -> Chat 3;
- Integration / Chat 3 -> Chat 4;
- Integration / Chat 4 -> Chat 5.

The Round-3 golden job is candidate-only and is expected to be skipped on main.

## Candidate CI evidence

**Authoritative candidate run:** `36638965404`  
**Workflow:** `MREA CI`  
**Event:** `push`  
**Head SHA:** `199cf5a15a22a6b6a01b54540f5f856a18ca7752`  
**Status:** `completed`  
**Conclusion:** `success`

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

All mandatory boundary jobs were actually executed. None of the four boundary gates or the golden-path gate is accepted as `skipped`.

The golden-path job step `Run Round 3 Capture -> Physical Instance golden path` completed `SUCCESS`.

## External gates

The following remain explicitly external/unverified:

- real Windows 11 x64 + SOLIDWORKS 2026 COM execution;
- production C#/.NET Framework build against installed official SOLIDWORKS interop assemblies;
- real native `.SLDPRT` generation/verification on a controlled SOLIDWORKS host.

Status:

`EXTERNAL_GATE_UNVERIFIED`

These are not represented as PASS by Linux CI or TestDouble CAD evidence.

## Known limitations

- real-host SOLIDWORKS validation remains external;
- the software golden path uses the generic `TestDoubleCadAdapter` for CAD read-back verification;
- worker-specific limitations documented in each frozen Pass-3 handoff remain in force;
- this Stage-2 report does not accept any Pass-4/Pass-5 work into Round 3.

## Handoff to Chat 8

```text
Round 3 Stage 2 verdict:
CANDIDATE_READY_FOR_FINAL_REVIEW

Candidate branch:
integration/pass-3-candidate

Exact tested candidate SHA:
199cf5a15a22a6b6a01b54540f5f856a18ca7752

Candidate CI run:
36638965404 — SUCCESS

External gate:
REAL SOLIDWORKS 2026 HOST = EXTERNAL_GATE_UNVERIFIED
```

Chat 7 does not merge the candidate into `main` and does not close the round. Final Review, final merge decision, post-merge main CI, and round closure remain owned by Chat 8.