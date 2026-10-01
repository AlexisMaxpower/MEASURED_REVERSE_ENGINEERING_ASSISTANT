from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, pi
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .contracts import CanonicalGeometryInput, _apply_homography
from .core import GeometryPipeline
from .models import Arc, Circle, GeometryPrimitive, Line, Point2D
from .sketch_package import SketchPackageBuilder


@dataclass(frozen=True, slots=True)
class CandidateIssue:
    issue_id: str
    code: str
    message: str
    entity_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        result = {
            "unresolved_id": self.issue_id,
            "code": self.code,
            "message": self.message,
        }
        if self.entity_ids:
            result["entity_ids"] = list(self.entity_ids)
        return result


@dataclass(frozen=True, slots=True)
class GeometryExtractionResult:
    primitives: tuple[GeometryPrimitive, ...]
    issues: tuple[CandidateIssue, ...]


class VisionGeometryPipeline:
    """Compose image candidates with existing measurement/sketch logic."""

    def __init__(self) -> None:
        self.geometry = GeometryPipeline()
        self.builder = SketchPackageBuilder()

    def build_sketch(
        self,
        extraction: GeometryExtractionResult,
        context: CanonicalGeometryInput,
        *,
        sketch_package_id: str,
    ) -> dict:
        draft = self.geometry.build(extraction.primitives, context.measurements)
        package = self.builder.build(draft, context, sketch_package_id=sketch_package_id)
        package["unresolved"].extend(
            issue.to_dict()
            for issue in sorted(extraction.issues, key=lambda item: item.issue_id)
        )
        return package


class ImageGeometryExtractor:
    """OpenCV-backed, fail-closed v1 LINE/CIRCLE/ARC candidate extraction."""

    def __init__(
        self,
        *,
        polygon_epsilon_ratio: float = 0.01,
        min_contour_area_px: float = 8.0,
        circle_circularity_min: float = 0.70,
        ambiguity_area_ratio: float = 0.25,
        coordinate_precision: int = 3,
    ) -> None:
        if not 0 < polygon_epsilon_ratio < 1:
            raise ValueError("polygon_epsilon_ratio must be between 0 and 1")
        if min_contour_area_px <= 0:
            raise ValueError("min_contour_area_px must be positive")
        if not 0 < circle_circularity_min <= 1:
            raise ValueError("circle_circularity_min must be in (0, 1]")
        if not 0 < ambiguity_area_ratio <= 1:
            raise ValueError("ambiguity_area_ratio must be in (0, 1]")
        self.polygon_epsilon_ratio = polygon_epsilon_ratio
        self.min_contour_area_px = min_contour_area_px
        self.circle_circularity_min = circle_circularity_min
        self.ambiguity_area_ratio = ambiguity_area_ratio
        self.coordinate_precision = coordinate_precision

    def extract_profile(
        self, image_path: str | Path, homography: Iterable[float]
    ) -> GeometryExtractionResult:
        binary = self._mask(self._load(image_path))
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours or hierarchy is None:
            return self._issue(
                "U-VISION-NO-CONTOUR",
                "NO_REFERENCE_CONTOUR",
                "No observable foreground contour was found in the reference image.",
            )

        h = self._homography(homography)
        rows = hierarchy[0]
        outer = [
            i
            for i, row in enumerate(rows)
            if int(row[3]) == -1
            and cv2.contourArea(contours[i]) >= self.min_contour_area_px
        ]
        if not outer:
            return self._issue(
                "U-VISION-NO-DOMINANT-CONTOUR",
                "NO_DOMINANT_REFERENCE_CONTOUR",
                "No sufficiently large outer contour was found.",
            )
        outer.sort(key=lambda i: (-cv2.contourArea(contours[i]), i))
        largest = cv2.contourArea(contours[outer[0]])
        if any(
            cv2.contourArea(contours[i]) >= largest * self.ambiguity_area_ratio
            for i in outer[1:]
        ):
            return self._issue(
                "U-VISION-AMBIGUOUS-OUTER",
                "AMBIGUOUS_OUTER_CONTOUR",
                "Multiple similarly significant outer contours are visible; no part profile was selected silently.",
            )

        outer_index = outer[0]
        contour = contours[outer_index]
        approx = cv2.approxPolyDP(
            contour,
            self.polygon_epsilon_ratio * cv2.arcLength(contour, True),
            True,
        )
        primitives: list[GeometryPrimitive] = []
        issues: list[CandidateIssue] = []
        if len(approx) == 4:
            vertices = [
                self._tx(Point2D(float(v[0][0]), float(v[0][1])), h)
                for v in approx
            ]
            primitives.extend(self._quad_lines(vertices))
        else:
            issues.append(
                CandidateIssue(
                    "U-VISION-OUTER-NONQUAD",
                    "UNSUPPORTED_OUTER_CONTOUR",
                    f"Dominant outer contour approximated to {len(approx)} vertices; only reliable quadrilateral LINE candidates are promoted.",
                )
            )

        scale = self._similarity_scale(h)
        circles: list[tuple[Point2D, float, float]] = []
        for i, row in enumerate(rows):
            if int(row[3]) != outer_index:
                continue
            inner = contours[i]
            area = cv2.contourArea(inner)
            perimeter = cv2.arcLength(inner, True)
            if area < self.min_contour_area_px or perimeter <= 0:
                continue
            circularity = 4 * pi * area / (perimeter * perimeter)
            if circularity < self.circle_circularity_min:
                issues.append(
                    CandidateIssue(
                        f"U-VISION-INNER-{i:03d}",
                        "UNSUPPORTED_INNER_CONTOUR",
                        "An inner contour was observable but was not circular enough to promote as CIRCLE.",
                    )
                )
                continue
            if scale is None:
                issues.append(
                    CandidateIssue(
                        f"U-VISION-CIRCLE-XFORM-{i:03d}",
                        "CIRCLE_REQUIRES_SIMILARITY_TRANSFORM",
                        "A circular image feature was detected, but calibration does not preserve circles; no circle was invented in MAT_XY_MM.",
                    )
                )
                continue
            (cx, cy), radius_px = cv2.minEnclosingCircle(inner)
            circles.append(
                (
                    self._tx(Point2D(cx, cy), h),
                    self._q(radius_px * scale),
                    circularity,
                )
            )

        circles.sort(key=lambda item: (item[0].x, item[0].y, item[1]))
        for n, (center, radius, circularity) in enumerate(circles, 1):
            primitives.append(
                Circle(
                    f"C-HOLE-{n}",
                    center,
                    radius,
                    f"HOLE_{n}",
                    "VISION_DETECTED",
                    self._q(min(0.99, circularity)),
                )
            )
        return GeometryExtractionResult(
            tuple(sorted(primitives, key=lambda item: item.entity_id)),
            tuple(sorted(issues, key=lambda item: item.issue_id)),
        )

    def extract_open_arcs(
        self, image_path: str | Path, homography: Iterable[float]
    ) -> GeometryExtractionResult:
        binary = self._mask(self._load(image_path))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        h = self._homography(homography)
        scale = self._similarity_scale(h)
        if scale is None:
            return self._issue(
                "U-VISION-ARC-XFORM",
                "ARC_REQUIRES_SIMILARITY_TRANSFORM",
                "Open circular curves require calibration that preserves circles/arcs.",
            )

        components = [
            (label, int(stats[label, cv2.CC_STAT_AREA]))
            for label in range(1, count)
            if int(stats[label, cv2.CC_STAT_AREA]) >= 8
        ]
        components.sort(key=lambda item: (-item[1], item[0]))
        arcs: list[Arc] = []
        issues: list[CandidateIssue] = []
        for ordinal, (label, _) in enumerate(components, 1):
            ys, xs = np.where(labels == label)
            points = np.column_stack((xs, ys)).astype(np.float32)
            (cx, cy), radius_px = cv2.minEnclosingCircle(points)
            radial = np.sqrt((points[:, 0] - cx) ** 2 + (points[:, 1] - cy) ** 2)
            rms = float(np.sqrt(np.mean((radial - radius_px) ** 2)))
            if rms > 1.25:
                issues.append(
                    CandidateIssue(
                        f"U-VISION-OPEN-{ordinal:03d}",
                        "OPEN_CURVE_NOT_CIRCULAR",
                        "An open image component was detected but does not fit a circular arc reliably enough.",
                    )
                )
                continue
            center = self._tx(Point2D(cx, cy), h)
            mat_points = [
                self._tx(Point2D(float(x), float(y)), h)
                for x, y in zip(xs.tolist(), ys.tolist())
            ]
            start, end, coverage = self._arc_span(center, mat_points)
            if coverage < 25 or coverage > 330:
                issues.append(
                    CandidateIssue(
                        f"U-VISION-OPEN-{ordinal:03d}",
                        "AMBIGUOUS_ARC_COVERAGE",
                        f"Circular open-curve coverage {coverage:.3f} deg is outside the reliable ARC promotion range.",
                    )
                )
                continue
            arcs.append(
                Arc(
                    f"A-DETECTED-{ordinal:03d}",
                    center,
                    self._q(radius_px * scale),
                    self._q(start),
                    self._q(end),
                    None,
                    "VISION_DETECTED",
                    self._q(max(0.0, min(0.99, 0.99 - rms / max(radius_px, 1.0)))),
                )
            )
        if not arcs and not issues:
            issues.append(
                CandidateIssue(
                    "U-VISION-NO-OPEN-CURVE",
                    "NO_RELIABLE_OPEN_ARC",
                    "No reliable open circular arc candidate was observable.",
                )
            )
        return GeometryExtractionResult(tuple(arcs), tuple(issues))

    def _quad_lines(self, vertices: list[Point2D]) -> list[Line]:
        cx = sum(p.x for p in vertices) / 4
        cy = sum(p.y for p in vertices) / 4
        points = sorted(vertices, key=lambda p: atan2(p.y - cy, p.x - cx))
        segments = [(points[i], points[(i + 1) % 4]) for i in range(4)]
        mids = [Point2D((a.x + b.x) / 2, (a.y + b.y) / 2) for a, b in segments]
        min_x, max_x = min(p.x for p in mids), max(p.x for p in mids)
        min_y, max_y = min(p.y for p in mids), max(p.y for p in mids)
        tolerance = max(max_x - min_x, max_y - min_y, 1.0) * 0.02
        found: dict[str, tuple[Point2D, Point2D]] = {}
        generic: list[tuple[Point2D, Point2D]] = []
        for (a, b), mid in zip(segments, mids):
            if abs(b.y - a.y) <= tolerance:
                key = "EDGE_BOTTOM" if abs(mid.y - min_y) <= abs(mid.y - max_y) else "EDGE_TOP"
                found[key] = (a, b)
            elif abs(b.x - a.x) <= tolerance:
                key = "EDGE_LEFT" if abs(mid.x - min_x) <= abs(mid.x - max_x) else "EDGE_RIGHT"
                found[key] = (a, b)
            else:
                generic.append((a, b))
        result: list[Line] = []
        for feature, entity_id in [
            ("EDGE_BOTTOM", "L-BOTTOM"),
            ("EDGE_RIGHT", "L-RIGHT"),
            ("EDGE_TOP", "L-TOP"),
            ("EDGE_LEFT", "L-LEFT"),
        ]:
            if feature not in found:
                continue
            a, b = self._orient(feature, *found[feature])
            result.append(Line(entity_id, a, b, feature, "VISION_DETECTED", 0.99))
        for n, (a, b) in enumerate(sorted(generic, key=lambda s: (s[0], s[1])), 1):
            result.append(Line(f"L-DETECTED-{n:03d}", a, b, None, "VISION_DETECTED", 0.90))
        return result

    @staticmethod
    def _orient(feature: str, a: Point2D, b: Point2D) -> tuple[Point2D, Point2D]:
        swap = (
            (feature == "EDGE_BOTTOM" and a.x > b.x)
            or (feature == "EDGE_RIGHT" and a.y > b.y)
            or (feature == "EDGE_TOP" and a.x < b.x)
            or (feature == "EDGE_LEFT" and a.y < b.y)
        )
        return (b, a) if swap else (a, b)

    @staticmethod
    def _load(path: str | Path) -> np.ndarray:
        image = cv2.imread(str(Path(path)), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"reference image could not be decoded: {path}")
        return image

    @staticmethod
    def _mask(image: np.ndarray) -> np.ndarray:
        return cv2.threshold(
            image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
        )[1]

    @staticmethod
    def _homography(values: Iterable[float]) -> tuple[float, ...]:
        result = tuple(float(value) for value in values)
        if len(result) != 9:
            raise ValueError("homography must contain exactly 9 coefficients")
        return result

    def _tx(self, point: Point2D, h: tuple[float, ...]) -> Point2D:
        transformed = _apply_homography(point, h)
        return Point2D(self._q(transformed.x), self._q(transformed.y))

    def _q(self, value: float) -> float:
        value = round(float(value), self.coordinate_precision)
        return 0.0 if value == -0.0 else value

    @staticmethod
    def _similarity_scale(h: tuple[float, ...], tolerance: float = 1e-6) -> float | None:
        if abs(h[6]) > tolerance or abs(h[7]) > tolerance or abs(h[8]) <= 1e-12:
            return None
        a, b, d, e = h[0] / h[8], h[1] / h[8], h[3] / h[8], h[4] / h[8]
        first, second = hypot(a, d), hypot(b, e)
        if first <= 1e-12 or second <= 1e-12:
            return None
        scale = (first + second) / 2
        if abs(first - second) > tolerance * max(scale, 1.0):
            return None
        if abs(a * b + d * e) > tolerance * max(first * second, 1.0):
            return None
        return scale

    @staticmethod
    def _arc_span(center: Point2D, points: list[Point2D]) -> tuple[float, float, float]:
        angles = sorted(
            degrees(atan2(p.y - center.y, p.x - center.x)) % 360 for p in points
        )
        gaps = []
        for i, angle in enumerate(angles):
            nxt = angles[(i + 1) % len(angles)] + (360 if i == len(angles) - 1 else 0)
            gaps.append((nxt - angle, i))
        largest, index = max(gaps, key=lambda item: (item[0], -item[1]))
        return angles[(index + 1) % len(angles)], angles[index], 360 - largest

    @staticmethod
    def _issue(issue_id: str, code: str, message: str) -> GeometryExtractionResult:
        return GeometryExtractionResult((), (CandidateIssue(issue_id, code, message),))
