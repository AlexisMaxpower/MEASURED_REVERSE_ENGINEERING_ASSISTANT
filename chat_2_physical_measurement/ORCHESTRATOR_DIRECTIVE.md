# ORCHESTRATOR DIRECTIVE — Chat 2
**Revision:** OD-2026-09-29-002  
**Pass:** 2  
**Owner:** Chat 6  
**Round 1 verdict:** ACCEPTED AS SLICE

Read before Pass 2 implementation.

## Branch policy

Pass 2 work MUST be performed on:

`chat-2/pass-2`

Do not commit Pass 2 implementation directly to `main`.

## Canonical inputs
- `core/contracts/mrea_contracts_v1.schema.json`
- `core/contracts/POLICIES_V1.md`
- `tests/fixtures/contracts/capture_package_v1.json`
- `tests/fixtures/contracts/measurement_package_v1.json`

## Accepted baseline

OD-001 is closed for Chat 2. The raw Phase A measurement boundary is accepted.

Important: current manual anchors being emitted as `IMAGE_PX` is intentional and remains valid. Do NOT silently convert them to MAT_XY_MM inside the measurement slice merely to satisfy Chat 3.

Coordinate normalization belongs to the geometry boundary because Chat 3 receives both measurement anchors and CapturePackage calibration.

## Pass 2 priority — harden real raw measurement output

1. Keep manual raw anchors/evidence in `IMAGE_PX`.
2. Preserve clean-reference ID, evidence frame ID, provenance and explicit user confirmation.
3. Add slice-local integration specimens/tests representing actual Chat 2 output, not the pre-normalized Integrator golden fixture.
4. Cover at least:
   - linear external measurement;
   - internal diameter or diameter measurement;
   - multiple verified measurements in one package;
   - `feature_id = null` as a valid current raw-capture state;
   - evidence frame linkage when an evidence frame exists.
5. Make deterministic ID injection available in tests so downstream cross-slice tests can reproduce actual Chat 2 wire output.
6. If touching uncertainty internals, move toward unit-neutral semantics; do not break current canonical v1 contract just to rename an internal field.

## Cross-slice requirement

The output produced by this pass must be suitable as the raw input specimen for Chat 3's new IMAGE_PX → MAT_XY_MM normalization tests.

No new shared contract is required for this fix.

## Do not

- move homography/geometry normalization into Chat 2;
- assign inferred geometry `feature_id` values without actual feature detection;
- allow OCR/voice to become verified without explicit confirmation policy;
- edit shared contracts/fixtures.

## Acceptance target

A deterministic, schema-valid MeasurementPackage generated from actual Chat 2 internals with raw IMAGE_PX anchors, multiple measurements and preserved evidence/provenance.

## Required handoff

Update `ORCHESTRATOR_HANDOFF.md` with Pass 2 branch, final SHA, exact tests executed, limitations and requested acceptance gate.
