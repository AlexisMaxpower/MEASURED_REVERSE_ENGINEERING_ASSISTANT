# Chat 2 — Pass 8 Implementation Report

## Baseline

Pass 8 is stacked on frozen Pass-7 head:

`d9b0471ecf1da38ee03759d9de8d4f2d03686939`

Worker branch:

`chat-2/pass-8`

At pass start PR #32 was still open and Chat-6 directive/state files on `main` were still formally on Pass 3. This is therefore a stacked worker pass, not a claim of a new Chat-6 directive.

## Problem closed

Chat 2 already allowed `OCR_MEASURED` candidates through the provider-independent hands-free state machine, but had no OCR-specific input boundary. Raw OCR text could not yet be deterministically classified as a safe measurement proposal.

Pass 8 adds the Phase-C domain/application OCR baseline.

## Provider-neutral OCR domain

Added `src/physical_measurement/ocr.py` with:

- `OcrObservation`;
- `OcrMeasurementReader`;
- `OcrMeasurementProposal`;
- `OcrReadResult`;
- `OcrReadStatus`;
- `OcrMeasurementPipeline`;
- `OcrPipelineResult`.

No OCR vendor SDK is required for correctness. A future Tesseract/EasyOCR/PaddleOCR/etc. adapter only has to produce an `OcrObservation`.

## Deterministic parsing

The reader accepts one strict numeric value with optional supported unit:

- decimal dot or comma;
- `mm` / `мм`;
- `deg` / `°` / narrow Russian degree aliases;
- Unicode NFKC normalization, including full-width digits.

Results are explicit:

- `VALUE`;
- `NO_VALUE`;
- `AMBIGUOUS`;
- `INVALID`;
- `UNIT_MISMATCH`.

Multiple numeric values never produce an arbitrary winner. Text containing a single number plus unrelated OCR junk is rejected as `INVALID` rather than guessed.

## Unit truth

`OcrMeasurementPipeline` does not accept a caller-selected expected unit. The expected unit is derived from `MeasurementTypeRegistry` using the active measurement type.

Examples:

- linear / diameter / depth measurement types -> `mm`;
- `ANGLE` -> `deg`.

This prevents an OCR adapter from declaring a unit inconsistent with the actual measurement type.

## Evidence/context binding

An OCR pipeline requires `evidence_frame_id` in `MeasurementCandidateContext`.

Before a proposal can become a candidate, the observation must match the active context on:

- `view_id`;
- anchor `reference_frame_id`;
- `evidence_frame_id`.

Metadata mismatch fails closed before any measurement is created.

## Verification semantics

A successful OCR read calls the existing hands-free candidate transition with:

`source = OCR_MEASURED`

The resulting `PhysicalMeasurement` remains:

- `verified = false`;
- source `OCR_MEASURED`;
- linked to the existing evidence frame and raw `IMAGE_PX` anchors.

OCR confidence is evidence only. Even `confidence=1.0` does not auto-verify the value.

Verification still requires the existing explicit confirmation transition and records:

`confirmation_source = USER_CONFIRMED`

The original measurement source remains `OCR_MEASURED`.

## Existing state machine reuse

`HandsFreeMeasurementController` now exposes its immutable `MeasurementCandidateContext` through a read-only property so provider-neutral adapters can validate themselves against the exact measurement context.

No duplicate OCR-specific confirmation state machine was introduced.

## Files changed in Pass 8

Modified:

- `src/physical_measurement/hands_free.py`
- `src/physical_measurement/__init__.py`

Added:

- `src/physical_measurement/ocr.py`
- `tests/test_pass8_ocr_pipeline.py`
- `docs/PASS_8_BUILD_REUSE_CHECK.md`
- `docs/IMPLEMENTATION_REPORT_PASS_8.md`

`ORCHESTRATOR_HANDOFF.md` is updated only after implementation CI is green.

No shared canonical contract, fixture, CI workflow, Chat-3 implementation, or other chat-owned slice is modified.

## Tests

`tests/test_pass8_ocr_pipeline.py` covers:

1. decimal comma + mm parsing;
2. degree-symbol parsing;
3. NFKC/full-width numeric normalization;
4. `NO_VALUE`, `AMBIGUOUS`, and junk-text `INVALID` outcomes;
5. explicit unit mismatch;
6. unit derivation from `MeasurementTypeRegistry`;
7. mandatory evidence context;
8. view/reference/evidence mismatch fail-closed behavior;
9. non-value OCR results create no measurement;
10. `confidence=1.0` still creates only an unverified candidate;
11. OCR candidate requires the same explicit user confirmation transition;
12. canonical output preserves `OCR_MEASURED`, `USER_CONFIRMED`, evidence linkage and raw `IMAGE_PX` anchors;
13. `ANGLE` OCR candidates use `deg`.

## Remaining debt

- no actual OCR image engine/provider adapter yet;
- no display ROI detector yet;
- no OCR overlay/UI acceptance layer yet;
- provider confidence/raw text are retained in the proposal path but canonical v1 has no dedicated OCR-observation object;
- device/caliper protocol and automatic jaw/contact estimation remain future work.
