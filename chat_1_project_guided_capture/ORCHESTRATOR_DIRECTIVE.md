# ORCHESTRATOR DIRECTIVE — Chat 1
**Revision:** OD-2026-09-29-002  
**Pass:** 2  
**Owner:** Chat 6  
**Round 1 verdict:** ACCEPTED

Read this file before any Pass 2 implementation.

## Branch policy

Pass 2 work MUST be performed on:

`chat-1/pass-2`

Do not commit Pass 2 implementation directly to `main`.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/project_v1.json`
- `tests/fixtures/contracts/capture_package_v1.json`

## Accepted baseline

OD-001 is closed for Chat 1. Canonical Project/Capture serialization and the ChArUco calibration baseline are accepted as the Pass 1 integration baseline.

Do not rewrite that baseline unless a regression requires it.

## Pass 2 priority — perspective normalization

Implement a deterministic derived reference image path:

```text
immutable clean reference
+ stored IMAGE_PX → MAT_XY_MM homography
→ deterministic perspective-normalized/rectified raster
→ immutable derived artifact
→ explicit source → derived provenance
```

Requirements:

1. original clean reference remains immutable and retrievable;
2. derived artifact has its own artifact identity/hash;
3. provenance links derived artifact to source clean frame and calibration used;
4. use the existing calibration/homography rather than inventing a second calibration model;
5. add synthetic perspective-warp regression using known geometry;
6. failures/invalid homography are explicit;
7. do not fabricate a scalar calibration-quality score merely to fill `quality`.

## Integration context

Round 1 exposed a Chat 2 → Chat 3 coordinate-space gap. Chat 1 already publishes the required homography; therefore Chat 1 does NOT need to change the shared contract for that issue.

## Acceptance target

Demonstrate with tests:

- deterministic rectification from a synthetic perspective-distorted reference;
- preserved original artifact;
- explicit source/calibration provenance;
- canonical CapturePackage remains schema-valid and backward-compatible.

## Do not

- edit `core/contracts` or canonical fixtures;
- absorb measurement/geometry semantics;
- begin voice-trigger/native-camera work before the perspective-normalization gate unless this directive is revised.

## Required handoff

Update `ORCHESTRATOR_HANDOFF.md` with Pass 2 branch, final SHA, exact tests executed, limitations and requested acceptance gate.
