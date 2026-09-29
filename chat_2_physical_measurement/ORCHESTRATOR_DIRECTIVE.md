# ORCHESTRATOR DIRECTIVE — Chat 2
**Revision:** OD-2026-09-29-002  
**Owner:** Chat 6
**Pass:** 2  
**Branch:** `chat-2/pass-2`

## Accepted from Pass 1
The Phase A measurement domain and canonical `MeasurementPackage v1` adapter are accepted as a slice. Raw anchors may legitimately remain `IMAGE_PX`; Chat 2 must not silently convert them into metric coordinates.

## Pass 2 priority
Harden the real raw measurement boundary and evidence chain without absorbing Chat 3 geometry responsibilities.

Required:
- keep actual manual anchors in `IMAGE_PX` when captured in image space;
- preserve `reference_frame_id`, `view_id`, provenance and confirmation source;
- add/maintain a representative real-output specimen/test using canonical CapturePackage input;
- explicitly test wrong reference frame/view rejection;
- keep OCR/voice unverified until confirmation policy allows verification.

## Integration context
Round 1 exposed a real boundary gap: Chat 3 accepted only `MAT_XY_MM`. That conversion belongs to Chat 3 using CapturePackage calibration. Do not "fix" integration by falsifying Chat 2 coordinates.

## CI requirement
Push Pass 2 only to `chat-2/pass-2`. `.github/workflows/ci.yml` runs Chat 2 tests plus the real `Chat 2 -> Chat 3` integration gate. Chat 2 local output must remain truthful even if that cross-slice gate is red until Chat 3 is fixed. Record CI status in handoff.

## Do not
- edit canonical shared contracts/fixtures;
- pre-normalize anchors only to satisfy Chat 3;
- move geometry matching into Chat 2;
- commit Pass 2 implementation directly to `main`.

## Handoff
Finish with `ORCHESTRATOR_HANDOFF.md` per Chat 6 development workflow.
