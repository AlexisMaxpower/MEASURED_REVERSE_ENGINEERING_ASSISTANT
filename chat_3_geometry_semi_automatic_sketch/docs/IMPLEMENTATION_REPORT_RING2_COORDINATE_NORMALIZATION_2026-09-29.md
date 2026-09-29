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
6. explicit rejection zero homogeneous divisor;
7. wrong reference frame rejection;
8. missing calibration rejection;
9. degenerate homography rejection;
10. MAT_XY_MM pass-through без calibration lookup;
11. deterministic output при изменении порядка anchors.

## Runtime verification

Локальный workspace восстановлен из Ring 1 cumulative snapshot плюс exact current Integrator-owned contract blobs из GitHub.

Выполнено:

```text
cd chat_3_geometry_semi_automatic_sketch
python -m pytest -q
```

Результат:

```text
20 passed in 0.85s
```

Полный suite включает:

- 6 Phase 1 geometry-core tests;
- 4 existing canonical FRONT tests;
- 10 Ring 2 coordinate-normalization tests.

Также выполнялось:

```text
python -m compileall -q src tests
```

Результат: success, compile errors отсутствуют.

## Dependencies

Новых runtime dependencies нет. Сохраняются существующие test-only:

- `pytest >=8,<9`;
- `jsonschema >=4.23,<5`.

## Shared ownership

Ring 2 не изменяет:

- `core/contracts/`;
- `tests/fixtures/contracts/`;
- Chat 2 code;
- Chat 4 code;
- global architecture.

## Known limitations

- поддерживаются только canonical `IMAGE_PX` и `MAT_XY_MM`, как определено v1;
- normalization выполняется в рамках выбранного view; multi-view остаётся later work;
- локальный threshold для calibration `quality` не выдумывается: проверяются наличие, shape и numeric validity;
- raw image primitive extraction намеренно отложен активной директивой;
- missing/invalid calibration приводит к explicit adapter error, recovery через guessed scale отсутствует.

## Change Requests

None. Shared v1 contracts достаточны для Ring 2.

## Acceptance requested

Chat 6 должен проверить branch `chat-3/pass-2` и подтвердить gate:

```text
IMAGE_PX MeasurementPackage
+ valid CapturePackage calibration
→ MAT_XY_MM normalized geometry input
→ deterministic schema-valid SketchPackage
```

Только после acceptance этого gate Chat 3 должен переходить к OpenCV / primitive extraction.
