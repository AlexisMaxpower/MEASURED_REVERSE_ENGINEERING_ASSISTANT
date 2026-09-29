# BUILD / REUSE CHECK — R1 Phase 3 Calibration

**Date:** 2026-09-29

## Problem

MREA needs Measurement Mat detection, ChArUco control points and a planar transformation from source image pixels to the canonical `MAT_XY_MM` coordinate system.

## Existing open-source solution

YES.

OpenCV provides maintained ArUco/ChArUco primitives including:

- predefined marker dictionaries;
- `ArucoDetector`;
- `CharucoBoard`;
- `CharucoDetector`;
- ChArUco corner interpolation;
- `findHomography` / `perspectiveTransform`.

Current implementation was verified against OpenCV 4.13 API. Official OpenCV documentation states that ChArUco provides more accurate chessboard corner locations than plain ArUco and can tolerate partial visibility/occlusion. Without camera intrinsics, ChArUco detection can use homography-based interpolation.

## Can we reuse it?

YES.

## What we reuse

- OpenCV ArUco/ChArUco detection;
- OpenCV image decoding;
- robust homography estimation using RANSAC;
- perspective point transformation.

Python dependency baseline:

- `opencv-contrib-python-headless>=4.13,<5`;
- `numpy>=2,<3`.

The headless package is selected because Chat 1 does not depend on `cv2.imshow` or OpenCV GUI facilities.

## What MREA implements itself

- `MeasurementMatProfile` identity/version parameters;
- detector abstraction (`CalibrationDetector`);
- mapping to `MAT_XY_MM`;
- explicit clean-reference provenance through `source_frame_id`;
- capture-session persistence of calibration;
- calibration conflict/duplicate policy;
- canonical `CapturePackage.views[].calibration` mapping;
- tests and future quality acceptance policy;
- later perspective-normalized derived artifact and its provenance.

## Quality policy

Canonical `calibration.quality` currently remains `null`.

Reason: neither SSOT nor canonical contracts define a defensible scalar quality formula. The implementation stores objective evidence (`detected_marker_count`, `detected_charuco_corner_count`, `reprojection_rmse_mm`) rather than inventing an arbitrary score. A scalar quality policy must be defined explicitly before it is emitted.

## Lock-in risk

LOW/MEDIUM.

OpenCV-specific code is isolated behind `CalibrationDetector`. Domain/session models and canonical mapping do not depend on OpenCV objects or NumPy arrays.

## Fallback

A native mobile detector, another fiducial library, or a platform CV implementation can replace `OpenCvCharucoCalibrationDetector` without changing the Chat 1 domain contract.
