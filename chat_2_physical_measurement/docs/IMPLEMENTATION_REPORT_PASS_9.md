# Chat 2 — Pass 9 Implementation Report

## Baseline

Pass 9 is stacked on frozen Pass-8 head:

`2d3be8a285c76f0fd940850a083709d8559f97a1`

Worker branch:

`chat-2/pass-9`

At pass start PR #34 remained open, `main` remained on the Round-3 integration baseline, and Chat-2 / Chat-6 directive files were still formally on Pass 3. Pass 9 is therefore a stacked worker pass, not a claim of a new Chat-6 directive.

## Problem closed

Pass 8 introduced a provider-neutral OCR measurement pipeline, but it still assumed that some external component had already decided which rectangular display region should be sent to OCR.

Pass 9 adds the provider-neutral display ROI selection stage immediately before OCR.

## Display ROI domain

Added `src/physical_measurement/display_roi.py` with:

- `DisplayRoiCandidate`;
- `DisplayRoiSelector`;
- `DisplayRoiProposal`;
- `DisplayRoiSelection`;
- `RoiSelectionStatus`;
- `DisplayRoiOcrBridge`.

A detector candidate carries:

- opaque ROI id;
- `view_id`;
- `reference_frame_id`;
- `evidence_frame_id`;
- raw pixel bbox `(x, y, width, height)`;
- detector confidence;
- optional detector provider name;
- provenance `VISION_DETECTED`.

No OpenCV/model/vendor dependency is required by the selection policy.

## Deterministic selection

`DisplayRoiSelector` filters candidates to the exact active view/reference/evidence context and configured minimum confidence.

Outcomes are explicit:

- `MATCH` — one deterministic best candidate;
- `NO_MATCH` — nothing eligible;
- `AMBIGUOUS` — top confidence values fall within the configured ambiguity epsilon.

Duplicate ROI ids fail closed. Invalid/non-finite bbox or confidence fails closed.

Detector confidence is used only to choose an operational crop. It is never interpreted as confidence in the physical measurement value.

## ROI -> OCR bridge

`DisplayRoiOcrBridge` builds an `OcrObservation` from a selected ROI and external OCR text.

`OcrObservation` / `OcrMeasurementProposal` now optionally preserve:

- `roi_id`;
- `roi_bbox_px`;
- `roi_confidence`;
- `roi_provider_name`.

Partial or invalid ROI metadata fails closed. Existing OCR observations without ROI metadata remain backward compatible.

The existing `OcrMeasurementPipeline` still performs the authoritative measurement-context check against the active `MeasurementCandidateContext`. Therefore a selected ROI from another view/reference/evidence frame cannot be used to create a measurement candidate.

## Physical truth invariants

Pass 9 does not add automatic verification.

Even with ROI detector confidence `1.0` and OCR confidence `1.0`:

- result enters as source `OCR_MEASURED`;
- measurement remains `verified = false`;
- explicit user confirmation is still required;
- raw measurement anchors stay `IMAGE_PX`;
- geometry normalization remains Chat 3 ownership.

## Files changed in Pass 9

Modified:

- `src/physical_measurement/ocr.py`
- `src/physical_measurement/__init__.py`

Added:

- `src/physical_measurement/display_roi.py`
- `tests/test_pass9_display_roi.py`
- `docs/PASS_9_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_9.md`

`ORCHESTRATOR_HANDOFF.md` is updated only after implementation CI is green.

No file outside `chat_2_physical_measurement/` is modified.

## Tests

`tests/test_pass9_display_roi.py` verifies:

1. highest-confidence ROI is selected inside exact context;
2. wrong-context candidates produce `NO_MATCH`;
3. near-tied candidates produce `AMBIGUOUS`;
4. duplicate ROI ids fail closed;
5. invalid bbox fails closed;
6. ROI metadata survives the bridge into `OcrMeasurementProposal`;
7. ROI + OCR confidence cannot auto-verify a measurement;
8. wrong-context ROI is rejected by the existing OCR pipeline;
9. pre-Pass-9 OCR observations without ROI metadata remain valid.

## Remaining debt

- no actual display detector/model adapter yet;
- no image crop execution layer yet;
- no UI overlay for ROI preview/override yet;
- no hardware device/caliper protocol yet;
- no automatic caliper jaw/contact estimation yet;
- canonical v1 still has no dedicated OCR/ROI evidence object, so ROI metadata remains internal to Chat 2.
