from __future__ import annotations

from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, model_validator

from .artifacts import ArtifactStore
from .models import (
    CalibrationResult,
    CaptureQualityFinding,
    CaptureQualityMetrics,
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureViewType,
    FrameKind,
    MeasurementMatProfile,
    QualityReasonCode,
    QualitySeverity,
    StrictModel,
)
from .repositories import CaptureSessionRepository


class CaptureQualityError(RuntimeError):
    pass


class CaptureQualityPolicy(StrictModel):
    policy_version: str = "chat1.capture-quality.v1"
    blur_reject_laplacian_variance: float = Field(default=20.0, ge=0)
    blur_warn_laplacian_variance: float = Field(default=70.0, ge=0)
    mean_luma_reject_low: float = Field(default=25.0, ge=0, le=255)
    mean_luma_warn_low: float = Field(default=45.0, ge=0, le=255)
    mean_luma_warn_high: float = Field(default=210.0, ge=0, le=255)
    mean_luma_reject_high: float = Field(default=235.0, ge=0, le=255)
    clipped_warn_fraction: float = Field(default=0.08, ge=0, le=1)
    clipped_reject_fraction: float = Field(default=0.30, ge=0, le=1)
    glare_warn_fraction: float = Field(default=0.005, ge=0, le=1)
    glare_reject_fraction: float = Field(default=0.03, ge=0, le=1)
    glare_component_min_fraction: float = Field(default=0.0003, ge=0, le=1)
    glare_component_max_fraction: float = Field(default=0.03, ge=0, le=1)
    edge_density_reject: float = Field(default=0.003, ge=0, le=1)
    edge_density_warn: float = Field(default=0.01, ge=0, le=1)
    border_edge_warn_ratio: float = Field(default=0.22, ge=0, le=1)
    border_edge_reject_ratio: float = Field(default=0.45, ge=0, le=1)
    border_band_fraction: float = Field(default=0.08, gt=0, lt=0.5)
    marker_visibility_reject: float = Field(default=0.30, ge=0, le=1)
    marker_visibility_warn: float = Field(default=0.70, ge=0, le=1)
    dark_clip_threshold: int = Field(default=5, ge=0, le=255)
    bright_clip_threshold: int = Field(default=250, ge=0, le=255)
    glare_saturation_max: int = Field(default=40, ge=0, le=255)
    canny_low: int = Field(default=60, ge=0, le=255)
    canny_high: int = Field(default=140, ge=0, le=255)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "CaptureQualityPolicy":
        checks = [
            (self.blur_reject_laplacian_variance <= self.blur_warn_laplacian_variance, "blur"),
            (self.clipped_warn_fraction <= self.clipped_reject_fraction, "clipping"),
            (self.glare_warn_fraction <= self.glare_reject_fraction, "glare"),
            (self.glare_component_min_fraction <= self.glare_component_max_fraction, "glare component"),
            (self.edge_density_reject <= self.edge_density_warn, "edge density"),
            (self.border_edge_warn_ratio <= self.border_edge_reject_ratio, "border edge"),
            (self.marker_visibility_reject <= self.marker_visibility_warn, "marker visibility"),
            (self.canny_low < self.canny_high, "Canny"),
        ]
        for valid, label in checks:
            if not valid:
                raise ValueError(f"invalid {label} threshold order")
        if not (
            self.mean_luma_reject_low
            <= self.mean_luma_warn_low
            < self.mean_luma_warn_high
            <= self.mean_luma_reject_high
        ):
            raise ValueError("invalid mean-luma threshold order")
        return self


class CaptureQualityAnalyzer(Protocol):
    def analyze(
        self,
        image_bytes: bytes,
        *,
        source_frame_id: UUID,
        view: CaptureViewType,
        calibration: CalibrationResult | None = None,
        mat_profile: MeasurementMatProfile | None = None,
    ) -> CaptureQualityResult: ...


class OpenCvCaptureQualityAnalyzer:
    """Deterministic image-quality proxies; never physical measurement truth."""

    def __init__(self, policy: CaptureQualityPolicy | None = None) -> None:
        self.policy = policy or CaptureQualityPolicy()

    def analyze(
        self,
        image_bytes: bytes,
        *,
        source_frame_id: UUID,
        view: CaptureViewType,
        calibration: CalibrationResult | None = None,
        mat_profile: MeasurementMatProfile | None = None,
    ) -> CaptureQualityResult:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise CaptureQualityError("OpenCV vision dependencies are not installed") from exc

        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise CaptureQualityError("image bytes could not be decoded")
        if min(image.shape[:2]) < 16:
            raise CaptureQualityError("quality analysis requires an image of at least 16x16 pixels")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        total = float(gray.size)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        glare_mask = (
            (hsv[:, :, 2] >= self.policy.bright_clip_threshold)
            & (hsv[:, :, 1] <= self.policy.glare_saturation_max)
        ).astype("uint8")
        edges = cv2.Canny(gray, self.policy.canny_low, self.policy.canny_high)
        edge_pixels = int((edges > 0).sum())

        metrics = CaptureQualityMetrics(
            laplacian_variance=float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            mean_luma=float(gray.mean()),
            dark_clipped_fraction=float((gray <= self.policy.dark_clip_threshold).sum() / total),
            bright_clipped_fraction=float((gray >= self.policy.bright_clip_threshold).sum() / total),
            glare_proxy_fraction=self._glare_component_fraction(glare_mask),
            edge_density=float(edge_pixels / total),
            border_edge_ratio=self._border_edge_ratio(edges, edge_pixels),
            marker_corner_visibility=self._marker_visibility(calibration, mat_profile),
        )
        findings = self._findings(metrics)
        calibration_key = str(calibration.calibration_id) if calibration else "none"
        profile_key = mat_profile.mat_id if mat_profile else "none"
        analysis_id = uuid5(
            NAMESPACE_URL,
            f"mrea:capture-quality:v1:{source_frame_id}:{self.policy.policy_version}:{calibration_key}:{profile_key}",
        )
        return CaptureQualityResult(
            analysis_id=analysis_id,
            source_frame_id=source_frame_id,
            view=view,
            calibration_id=calibration.calibration_id if calibration else None,
            mat_id=mat_profile.mat_id if mat_profile else calibration.mat_id if calibration else None,
            policy_version=self.policy.policy_version,
            verdict=self._verdict(findings),
            metrics=metrics,
            findings=findings,
        )

    def _glare_component_fraction(self, mask) -> float:
        import cv2

        count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        total = float(mask.size)
        pixels = 0
        for label in range(1, count):
            area = int(stats[label, cv2.CC_STAT_AREA])
            fraction = area / total
            if self.policy.glare_component_min_fraction <= fraction <= self.policy.glare_component_max_fraction:
                pixels += area
        return float(min(1.0, pixels / total))

    def _border_edge_ratio(self, edges, edge_pixels: int) -> float:
        if edge_pixels == 0:
            return 0.0
        height, width = edges.shape
        band = max(1, int(round(min(height, width) * self.policy.border_band_fraction)))
        border = edges.copy()
        border[band : height - band, band : width - band] = 0
        return float((border > 0).sum() / edge_pixels)

    @staticmethod
    def _marker_visibility(
        calibration: CalibrationResult | None,
        mat_profile: MeasurementMatProfile | None,
    ) -> float | None:
        if calibration is None or mat_profile is None:
            return None
        if calibration.mat_id != mat_profile.mat_id:
            raise CaptureQualityError("calibration mat_id does not match the supplied mat profile")
        expected = (mat_profile.squares_x - 1) * (mat_profile.squares_y - 1)
        return float(min(1.0, calibration.detected_charuco_corner_count / expected))

    def _findings(self, m: CaptureQualityMetrics) -> list[CaptureQualityFinding]:
        p = self.policy
        findings: list[CaptureQualityFinding] = []
        self._low(findings, QualityReasonCode.BLUR, "laplacian_variance", m.laplacian_variance, p.blur_reject_laplacian_variance, p.blur_warn_laplacian_variance)
        self._low(findings, QualityReasonCode.UNDEREXPOSED, "mean_luma", m.mean_luma, p.mean_luma_reject_low, p.mean_luma_warn_low)
        self._high(findings, QualityReasonCode.OVEREXPOSED, "mean_luma", m.mean_luma, p.mean_luma_warn_high, p.mean_luma_reject_high)
        self._high(findings, QualityReasonCode.DARK_CLIPPING, "dark_clipped_fraction", m.dark_clipped_fraction, p.clipped_warn_fraction, p.clipped_reject_fraction)
        self._high(findings, QualityReasonCode.BRIGHT_CLIPPING, "bright_clipped_fraction", m.bright_clipped_fraction, p.clipped_warn_fraction, p.clipped_reject_fraction)
        self._high(findings, QualityReasonCode.GLARE_RISK, "glare_proxy_fraction", m.glare_proxy_fraction, p.glare_warn_fraction, p.glare_reject_fraction)
        self._low(findings, QualityReasonCode.LOW_SCENE_DETAIL, "edge_density", m.edge_density, p.edge_density_reject, p.edge_density_warn)
        self._high(findings, QualityReasonCode.FRAMING_BORDER_ACTIVITY, "border_edge_ratio", m.border_edge_ratio, p.border_edge_warn_ratio, p.border_edge_reject_ratio)
        if m.marker_corner_visibility is not None:
            self._low(findings, QualityReasonCode.LOW_MARKER_VISIBILITY, "marker_corner_visibility", m.marker_corner_visibility, p.marker_visibility_reject, p.marker_visibility_warn)
        return findings

    @staticmethod
    def _low(findings, code, metric: str, observed: float, reject: float, warn: float) -> None:
        if observed < reject:
            findings.append(CaptureQualityFinding(code=code, severity=QualitySeverity.REJECT, metric=metric, observed=observed, threshold=reject, comparison="<"))
        elif observed < warn:
            findings.append(CaptureQualityFinding(code=code, severity=QualitySeverity.WARN, metric=metric, observed=observed, threshold=warn, comparison="<"))

    @staticmethod
    def _high(findings, code, metric: str, observed: float, warn: float, reject: float) -> None:
        if observed > reject:
            findings.append(CaptureQualityFinding(code=code, severity=QualitySeverity.REJECT, metric=metric, observed=observed, threshold=reject, comparison=">"))
        elif observed > warn:
            findings.append(CaptureQualityFinding(code=code, severity=QualitySeverity.WARN, metric=metric, observed=observed, threshold=warn, comparison=">"))

    @staticmethod
    def _verdict(findings: list[CaptureQualityFinding]) -> CaptureQualityVerdict:
        if any(item.severity is QualitySeverity.REJECT for item in findings):
            return CaptureQualityVerdict.REJECT
        return CaptureQualityVerdict.WARN if findings else CaptureQualityVerdict.ACCEPT


class CaptureQualityService:
    def __init__(self, repository: CaptureSessionRepository, artifact_store: ArtifactStore, analyzer: CaptureQualityAnalyzer) -> None:
        self._repository = repository
        self._artifact_store = artifact_store
        self._analyzer = analyzer

    def analyze_clean_reference(
        self,
        session_id: UUID,
        *,
        view: CaptureViewType,
        mat_profile: MeasurementMatProfile | None = None,
    ) -> CaptureQualityResult:
        session = self._repository.get(session_id)
        clean = [frame for frame in session.frames if frame.view is view and frame.kind is FrameKind.CLEAN_REFERENCE]
        if len(clean) != 1:
            raise CaptureQualityError(f"view {view.value} requires exactly one clean reference frame")
        source = clean[0]
        calibration = next((item for item in session.calibrations if item.view is view), None)
        existing = next((item for item in session.quality_analyses if item.source_frame_id == source.frame_id), None)
        requested_calibration_id = calibration.calibration_id if calibration else None
        requested_mat_id = mat_profile.mat_id if mat_profile else calibration.mat_id if calibration else None
        if existing is not None:
            if existing.calibration_id == requested_calibration_id and existing.mat_id == requested_mat_id:
                return existing
            raise CaptureQualityError("quality analysis already exists for this frame with different calibration/mat context")

        result = self._analyzer.analyze(
            self._artifact_store.get_bytes(source.artifact),
            source_frame_id=source.frame_id,
            view=view,
            calibration=calibration,
            mat_profile=mat_profile,
        )
        session.quality_analyses.append(result)
        self._repository.save(session)
        return result


class RussianQualityGuidanceAdapter:
    _MESSAGES = {
        QualityReasonCode.BLUR: "Кадр размыт: зафиксируйте камеру и дождитесь фокусировки.",
        QualityReasonCode.UNDEREXPOSED: "Кадр слишком тёмный: добавьте свет или увеличьте экспозицию.",
        QualityReasonCode.OVEREXPOSED: "Кадр слишком светлый: уменьшите экспозицию или яркость освещения.",
        QualityReasonCode.DARK_CLIPPING: "Слишком много проваленных теней: осветите тёмные области детали.",
        QualityReasonCode.BRIGHT_CLIPPING: "Слишком много пересвеченных областей: уменьшите экспозицию или прямой свет.",
        QualityReasonCode.GLARE_RISK: "Есть риск бликов: измените угол камеры или источника света.",
        QualityReasonCode.LOW_SCENE_DETAIL: "В кадре мало различимых границ: проверьте фокус, масштаб и наличие детали.",
        QualityReasonCode.FRAMING_BORDER_ACTIVITY: "Значимые границы слишком близко к краю кадра: оставьте больше поля вокруг рабочей области.",
        QualityReasonCode.LOW_MARKER_VISIBILITY: "Плохо видны маркеры Measurement Mat: покажите большую часть мата без перекрытий.",
    }

    @classmethod
    def messages(cls, result: CaptureQualityResult) -> list[str]:
        if not result.findings:
            return ["Кадр пригоден для дальнейшего capture workflow."]
        return [cls._MESSAGES[item.code] for item in result.findings]
