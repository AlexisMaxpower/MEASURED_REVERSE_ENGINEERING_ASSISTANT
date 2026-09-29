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
