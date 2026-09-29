# Build / Reuse Check — Ring 2 Coordinate Normalization

**Дата:** 2026-09-29  
**Role:** Chat 3 — Geometry & Semi-Automatic Sketch  
**Directive:** `OD-2026-09-29-002`  
**Branch:** `chat-3/pass-2`

## Problem

Реальный canonical output Chat 2 сохраняет measurement anchors в `IMAGE_PX`, тогда как внутренний geometry pipeline Chat 3 работает в `MAT_XY_MM`. Ring 2 должен закрыть эту границу без изменения shared contracts и без угадывания масштаба.

## Existing solution / reuse

Переиспользуются без изменения:

- canonical `CapturePackage v1` calibration;
- canonical `MeasurementPackage v1` anchors;
- 3x3 homography, опубликованная upstream в CapturePackage view;
- существующий `CanonicalInputAdapter` как boundary owner;
- существующий `GeometryPipeline` и `SketchPackageBuilder` после normalization.

## Dependency decision

**Новая runtime dependency не добавляется.**

Для применения одной 3x3 homography достаточно детерминированной scalar arithmetic стандартной библиотеки Python. NumPy/OpenCV для этой операции не нужны и добавили бы лишний runtime surface.

OpenCV отдельно **не рассматривается в Ring 2**, потому что активная директива запрещает переходить к primitive extraction до зелёного coordinate-normalization gate.

## What Chat 3 builds

- validation 3x3 homography;
- finite-number checks;
- degeneracy check через determinant;
- homogeneous transform `IMAGE_PX → MAT_XY_MM`;
- safe homogeneous divide;
- clean-reference-frame verification;
- explicit errors при missing/invalid calibration;
- traceability полей `anchor_id`, `reference_frame_id`, `source_coordinate_space`;
- deterministic ordering normalized measurements.

## Why custom boundary code is required

Shared schema описывает homography и coordinate spaces, но не выполняет преобразование. Эта операция является integration responsibility Chat 3: она переводит wire-level evidence координаты в внутреннюю geometry coordinate system перед measurement binding.

## Failure policy

Запрещено:

- угадывать scale;
- принимать `IMAGE_PX` без calibration;
- игнорировать неправильный `reference_frame_id`;
- пропускать non-finite/degenerate transform;
- менять verified physical value при трансформации anchors.

Ошибки normalization завершаются явным `ValueError` на adapter boundary до создания geometry draft.

## Lock-in risk

Низкий. Реализация использует canonical mathematical representation 3x3 homography и не зависит от vendor-specific CV API.

## Future reuse

Когда будет разрешён OpenCV primitive extraction, detector сможет получать уже согласованную `MAT_XY_MM` boundary semantics, не дублируя measurement normalization.
