# Chat 3 — Ring 2 Implementation Report — Coordinate Normalization

**Дата:** 2026-09-29  
**Directive:** `OD-2026-09-29-002`  
**Pass / Ring:** 2  
**Branch:** `chat-3/pass-2`

## Problem closed

Round 1 integration review выявил несовместимость:

```text
Chat 2: IMAGE_PX anchors
Chat 3 Round 1: MAT_XY_MM-only adapter
```

Ring 2 добавляет явную coordinate-normalization boundary перед существующим geometry pipeline.

## Implemented

- `MAT_XY_MM` anchors проходят без geometric transform;
- `IMAGE_PX` anchors требуют совпадающий clean-reference frame;
- calibration должна публиковать `MAT_XY_MM` и 3x3 homography;
- коэффициенты и transformed result проверяются на finite values;
- degenerate homography отклоняется;
- применяется homogeneous transform и safe divide на `w`;
- verified physical value не изменяется;
- `AnchorRef` сохраняет `anchor_id`, `feature_id`, `reference_frame_id` и `source_coordinate_space`.

## Integration specimen

Добавлен:

`tests/fixtures/internal/chat2_image_px_measurement_package.json`

Он повторяет реальный wire shape Chat 2:

- `coordinate_space = IMAGE_PX`;
- `feature_id = null`;
- clean-reference `reference_frame_id`;
- verified manual measurement;
- canonical `MeasurementPackage v1` envelope.

Fixture отдельно валидируется против Integrator-owned `MeasurementPackage` schema.

## End-to-end acceptance path

```text
Chat-2-style IMAGE_PX MeasurementPackage
+ CapturePackage with non-identity homography
→ CanonicalInputAdapter
→ normalized MAT_XY_MM AnchorRef
→ GeometryPipeline
→ SketchPackageBuilder
→ schema-valid SketchPackage v1
```

## Ring 2 tests

`tests/test_coordinate_normalization.py` покрывает:

1. canonical schema validation Chat-2-style specimen;
2. non-identity IMAGE_PX → MAT_XY_MM transform;
3. `feature_id = null` coordinate fallback;
4. schema-valid downstream `SketchPackage`;
5. projective case с `w != 1` и homogeneous divide;
6. wrong reference frame rejection;
7. missing calibration rejection;
8. degenerate homography rejection;
9. MAT_XY_MM pass-through без calibration lookup;
10. deterministic output при изменении порядка anchors.
