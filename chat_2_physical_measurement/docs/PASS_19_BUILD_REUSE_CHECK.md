# Pass 19 Build / Reuse Check — OCR Measurement Pipeline

## Scope

Pass 19 implements the Chat-2 Phase-C domain/application boundary:

```text
LCD OCR provider output
+ exact display ROI / evidence frame
+ measurement type
→ deterministic OCR validation
→ unverified OCR_MEASURED candidate
→ existing explicit user confirmation path
```

The pass does **not** implement camera core, a concrete OCR SDK, CV display detection, caliper detection, geometry, CAD, or shared contracts.

## SSOT requirement

The SSOT names `DisplayRoiDetector` and `OcrMeasurementReader` under Chat-2 ownership and defines Phase C as `OCR proposes value`. It also states that OCR cannot silently become verified and recommends a ready on-device OCR engine with separate LCD-caliper validation.

## Reuse decision

### Reused

- Python standard library `re`, `unicodedata`, `Decimal`, dataclasses;
- existing `MeasurementTypeRegistry` as the unit truth source;
- existing `MeasurementSessionService.add_reported_candidate()` for candidate creation;
- existing `PhysicalMeasurement` provenance and explicit-confirmation rules;
- existing evidence-frame and anchor linkage.

### Not added

No OCR vendor/runtime dependency is added in this pass.

Reason:

1. provider choice belongs to the platform/integration layer and can vary by Android/iOS/runtime;
2. Chat 2 first needs deterministic truth semantics independent of provider behavior;
3. OCR engines may return malformed, ambiguous, mismatched-unit or low-confidence text, and those cases must not mutate measurement truth before validation;
4. adding a heavyweight OCR package to the domain test path would couple correctness to an implementation detail and make offline/provider substitution harder.

## Provider boundary

A future OCR adapter may emit `OcrTextObservation` with:

- raw OCR text;
- exact `DisplayRoi` in `IMAGE_PX`;
- `view_id`;
- `evidence_frame_id`;
- optional provider confidence;
- optional provider identifier.

`OcrMeasurementReader` then applies deterministic validation. It performs no character-guess correction (`O -> 0`, etc.), does not choose among multiple numeric readings, and validates explicit OCR units against `MeasurementTypeRegistry`.

## Future reuse candidates

A concrete on-device OCR engine remains a later integration choice. Selection should be based on the LCD dataset described in the SSOT (different values, angles, lighting, glare and device models) rather than introduced into the domain layer pre-emptively.
