# ORCHESTRATOR HANDOFF — Chat 2

**Pass:** 9  
**Branch:** `chat-2/pass-9`  
**Baseline:** frozen Pass-8 head `2d3be8a285c76f0fd940850a083709d8559f97a1`  
**Executable implementation SHA:** `236b42f48da04256303065f6f118606a988ea452`  
**Implementation CI:** `MREA CI` run `36659199031` / run #484  
**Date:** 2026-09-30  
**From:** Chat 2 — Physical Measurement  
**To:** Chat 6 / integration review

> This handoff is the final worker commit for Pass 9. The branch is frozen after this file update. No post-handoff worker commit should be added unless integration review explicitly returns a fix request.

## Orchestration note

Pass 9 is stacked on frozen Pass 8 because at pass start `main` remained on the Round-3 integration baseline and Chat-2 / Chat-6 directive files were still formally on `OD-2026-09-29-003 / Pass 3`. This handoff does not claim that Chat 6 issued a new Pass-9 directive.

## Delivered functionality

Pass 9 adds the provider-neutral display ROI selection stage before OCR.

Primary flow:

```text
external detector/provider
-> DisplayRoiCandidate(s)
-> DisplayRoiSelector
-> MATCH / NO_MATCH / AMBIGUOUS
-> DisplayRoiProposal
-> DisplayRoiOcrBridge
-> OcrObservation + ROI metadata
-> existing OcrMeasurementPipeline
-> unverified OCR_MEASURED candidate
-> explicit USER_CONFIRMED transition
```

## Deterministic ROI selection

`DisplayRoiSelector`:

- filters to exact `view_id`, `reference_frame_id`, `evidence_frame_id`;
- applies configured minimum detector confidence;
- selects highest-confidence eligible ROI;
- returns `AMBIGUOUS` when top candidates are within configured epsilon;
- returns `NO_MATCH` when nothing is eligible;
- rejects duplicate ROI ids;
- rejects invalid/non-finite bbox and confidence.

Detector confidence is used only to choose an operational crop. It is never treated as confidence in the physical measurement value.

## ROI -> OCR bridge

`DisplayRoiOcrBridge` constructs an `OcrObservation` from one selected ROI and external OCR text.

`OcrObservation` and `OcrMeasurementProposal` now optionally preserve:

- `roi_id`;
- `roi_bbox_px`;
- `roi_confidence`;
- `roi_provider_name`.

Partial/invalid ROI metadata fails closed. Existing OCR observations without ROI metadata remain backward compatible.

The existing OCR pipeline still validates view/reference/evidence against the active measurement context before creating a candidate.

## Physical truth protection

Even detector confidence `1.0` plus OCR confidence `1.0` still produces only an unverified `OCR_MEASURED` candidate. Explicit user confirmation remains mandatory and raw measurement anchors remain `IMAGE_PX`.

No geometry normalization moved into Chat 2.

## Files changed in Pass 9

Modified:

- `src/physical_measurement/ocr.py`
- `src/physical_measurement/__init__.py`
- `ORCHESTRATOR_HANDOFF.md`

Added:

- `src/physical_measurement/display_roi.py`
- `tests/test_pass9_display_roi.py`
- `docs/PASS_9_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_9.md`

No file outside `chat_2_physical_measurement/` was modified.

## Build / Reuse

Recorded in `docs/PASS_9_BUILD_REUSE_CHECK.md`.

Decision: PARTIAL reuse. Future OpenCV/detector/segmentation adapters may provide display-box candidates; MREA owns the context/ambiguity/selection policy and the ROI-to-OCR bridge.

## GitHub Actions evidence

Executable implementation state:

```text
run_id = 36659199031
run_number = 484
head_sha = 236b42f48da04256303065f6f118606a988ea452
conclusion = success
```

Required gates:

- `Chat 2 / Measurement` — `success`;
- `Contracts / canonical fixtures` — `success`;
- `Integration / Chat 1 -> Chat 2` — `success`;
- `Integration / Chat 2 -> Chat 3` — `success`.

## Known limitations / next debt

- no actual display detector/model adapter yet;
- no image crop execution layer yet;
- no ROI preview/override UI yet;
- no hardware device/caliper protocol yet;
- no automatic caliper jaw/contact estimation yet;
- canonical v1 has no dedicated OCR/ROI evidence object.

## Requested integration review

Verify:

1. ROI selection is deterministic and fails closed on no-match/ambiguity;
2. context binding prevents cross-view/reference/evidence ROI reuse;
3. ROI metadata survives into OCR proposals;
4. detector/OCR confidence cannot auto-verify a physical measurement;
5. old OCR observations without ROI metadata remain compatible;
6. required Chat-2 and adjacent integration gates are green on implementation SHA `236b42f48da04256303065f6f118606a988ea452`;
7. worker ownership remains slice-local.

If accepted, integrate after Pass 8 according to orchestrator ordering. This branch is frozen after this handoff commit.
