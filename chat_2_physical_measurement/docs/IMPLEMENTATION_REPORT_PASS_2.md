# IMPLEMENTATION REPORT — Chat 2 Pass 2

**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-2/pass-2`  
**Scope:** deterministic real raw `MeasurementPackage` output

## Delivered

Реализован воспроизводимый raw-output specimen, построенный через реальные Chat 2 internals:

```text
slice-local CapturePackage with evidence frame
→ MeasurementSessionService
→ manual LINEAR_EXTERNAL candidate
→ explicit USER_CONFIRMED
→ manual DIAMETER_INTERNAL candidate
→ explicit USER_CONFIRMED
→ CanonicalMeasurementAdapter
→ schema-valid MeasurementPackage
→ committed raw IMAGE_PX specimen
```

## Determinism

`MeasurementSessionService` теперь принимает optional `clock: Callable[[], datetime]` в дополнение к уже существующему `id_factory`.

Production default остаётся UTC system time. В тестах fixed timezone-aware clock делает `created_at`/confirmation timestamps воспроизводимыми.

Naive datetime от injected clock отклоняется.

## Raw specimen semantics

Committed fixture содержит:

- `LINEAR_EXTERNAL = 80.20 mm`;
- `DIAMETER_INTERNAL = 5.10 mm`;
- два verified measurements в одном package;
- `source = MANUAL_MEASURED`;
- `confirmation_source = USER_CONFIRMED`;
- `coordinate_space = IMAGE_PX`;
- `feature_id = null`;
- clean-reference linkage;
- real `evidence_frame_id` linkage;
- digital caliper instrument metadata;
- uncertainty `0.02 mm`;
- deterministic IDs and timestamps.

Slice-local CapturePackage сохраняет upstream calibration:

```text
MAT_XY_MM homography = [0.1,0,0,0,0.1,0,0,0,1]
```

Chat 2 намеренно НЕ применяет её. Координаты остаются raw IMAGE_PX. Это делает пару fixtures пригодной для Chat 3 normalization tests.

## Files changed/added

- `src/physical_measurement/service.py`
- `tests/test_pass2_raw_output.py`
- `tests/fixtures/capture_package_raw_image_px_v1.json`
- `tests/fixtures/measurement_package_raw_image_px_v1.json`
- `docs/BUILD_REUSE_CHECK_PASS_2.md`
- `docs/IMPLEMENTATION_REPORT_PASS_2.md`
- `ORCHESTRATOR_HANDOFF.md` (handoff commit)

## Verification

Local Chat 2 suite:

```text
13 passed in 1.11s
```

Test inventory added in Pass 2:

1. actual service+adapter output equals committed deterministic raw fixture;
2. raw specimen preserves two measurement types, verification/provenance/evidence, IMAGE_PX and null feature IDs;
3. injected clock makes session/measurement/confirmation timestamps deterministic;
4. naive injected clock is rejected.

## Not executed

- repository-wide suites for Chat 1/3/4/5;
- GitHub Actions (no Pass 2 CI run created by Chat 2);
- real mobile annotation UX;
- physical-device capture;
- Chat 3 normalization implementation/tests (owned by Chat 3).

## Contract impact

No shared contract or canonical fixture modified. No Change Request required.

## Limitations

- internal uncertainty field remains `uncertainty_mm`; no rename in this pass;
- current raw anchors have no detected `feature_id` by design;
- current Phase A still uses exactly two anchors per measurement internally;
- no OCR/voice/CV verification introduced.
