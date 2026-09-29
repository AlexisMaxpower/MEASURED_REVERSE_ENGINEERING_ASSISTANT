# IMPLEMENTATION_REPORT — Chat 1 R1 Phase 3 Calibration Baseline

## 1. Что реализовано

- `MeasurementMatProfile`;
- `CalibrationResult` persisted inside `CaptureSession`;
- `CalibrationDetector` protocol;
- `OpenCvCharucoCalibrationDetector`;
- ChArUco detection from clean-reference image bytes;
- homography `IMAGE_PX -> MAT_XY_MM` via RANSAC;
- objective detection evidence: marker count, ChArUco corner count, corner IDs, reprojection RMSE in mm;
- `CalibrationService` with explicit one-calibration-per-view policy;
- canonical `CapturePackage.views[].calibration` serialization;
- provenance check: calibration must reference the view's clean reference frame;
- synthetic ChArUco integration test.

## 2. Исходные contracts

- `core/contracts/mrea_contracts_v1.schema.json`;
- `core/contracts/POLICIES_V1.md`;
- `CapturePackage v1` calibration object.

Shared contracts were not modified.

## 3. Изменённые/добавленные файлы

- `src/mrea_capture/models.py`;
- `src/mrea_capture/calibration.py`;
- `src/mrea_capture/contracts.py`;
- `src/mrea_capture/__init__.py`;
- `tests/test_calibration.py`;
- `pyproject.toml`;
- `docs/BUILD_REUSE_CHECK_PHASE3_CALIBRATION.md`;
- this report;
- `docs/IMPLEMENTATION_STATE.md`.

## 4. Зависимости

Vision/test baseline:

- `numpy>=2,<3`;
- `opencv-contrib-python-headless>=4.13,<5`.

## 5. Тесты

Latest full local Chat 1 run:

```text
13 passed in 1.07s
```

Synthetic calibration test:

- generates a 5x7 ChArUco board;
- detects 24 ChArUco corners;
- detects ArUco markers;
- computes 3x3 homography;
- achieves reprojection RMSE `< 0.001 mm` on the synthetic fixture;
- persists calibration in CaptureSession;
- emits non-null canonical calibration;
- validates resulting CapturePackage against Integrator-owned JSON Schema.

## 6. Что не проверено

- real printed Measurement Mat;
- phone-camera lens distortion;
- glare, shadows, blur and oblique real-world captures;
- camera intrinsic calibration;
- physical mm accuracy against a ruler/caliper;
- perspective-normalized derived image artifact;
- mobile/native OpenCV integration;
- GitHub Actions CI.

## 7. Известные ограничения

- canonical `quality` remains `null` because no approved scalar quality policy exists;
- current homography assumes a planar mat and uses detected ChArUco control points;
- detector rejects fewer than 4 ChArUco corners;
- re-calibration of the same view is currently explicit error rather than silent replacement.

## 8. Change Requests

None.

## 9. Готово к интеграции

- schema-valid Project/Capture adapter;
- ChArUco calibration result in `MAT_XY_MM`;
- canonical CapturePackage with non-null calibration.

## 10. Следующий шаг

Perspective normalization: create a derived rectified image artifact from the clean reference using the stored homography, preserve source -> derived provenance, and test deterministic geometry on synthetic perspective-distorted fixtures.
