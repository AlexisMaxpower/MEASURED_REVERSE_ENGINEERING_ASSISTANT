from __future__ import annotations

from enum import StrEnum
from math import hypot, isfinite
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, model_validator

from .lineage import active_clean_reference, calibration_for_active_reference
from .models import CaptureSession, CaptureViewType, StrictModel


class CaptureAlignmentError(RuntimeError):
    pass


class CaptureAlignmentSeverity(StrEnum):
    WARN = "WARN"
    REJECT = "REJECT"


class CaptureAlignmentVerdict(StrEnum):
    ACCEPT = "ACCEPT"
    WARN = "WARN"
    REJECT = "REJECT"


class CaptureAlignmentReasonCode(StrEnum):
    CAMERA_TILT_RISK = "CAMERA_TILT_RISK"
    PERSPECTIVE_DISTORTION_RISK = "PERSPECTIVE_DISTORTION_RISK"


class CaptureAlignmentAction(StrEnum):
    CONTINUE_CAPTURE_WORKFLOW = "CONTINUE_CAPTURE_WORKFLOW"
    REALIGN_CAMERA_PERPENDICULAR = "REALIGN_CAMERA_PERPENDICULAR"
    REDUCE_PERSPECTIVE_DISTORTION = "REDUCE_PERSPECTIVE_DISTORTION"


class CaptureAlignmentPolicy(StrictModel):
    """Versioned camera-alignment guidance policy; never camera-pose or metrology truth."""

    policy_version: str = "chat1.capture-alignment.v1"
    check_camera_tilt: bool = True
    check_perspective_distortion: bool = True
    camera_tilt_warn_proxy: float = Field(default=0.25, ge=0, le=1)
    camera_tilt_reject_proxy: float = Field(default=0.50, ge=0, le=1)
    perspective_warn_scale_ratio: float = Field(default=1.35, ge=1)
    perspective_reject_scale_ratio: float = Field(default=2.00, ge=1)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "CaptureAlignmentPolicy":
        if self.camera_tilt_warn_proxy >= self.camera_tilt_reject_proxy:
            raise ValueError("camera tilt warn threshold must be lower than reject threshold")
        if self.perspective_warn_scale_ratio >= self.perspective_reject_scale_ratio:
            raise ValueError("perspective warn threshold must be lower than reject threshold")
        return self


class CaptureAlignmentMetrics(StrictModel):
    """Dimensionless projective-geometry proxies derived from calibration homography."""

    camera_tilt_proxy: float = Field(ge=0, le=1)
    perspective_scale_ratio: float = Field(ge=1)


class CaptureAlignmentFinding(StrictModel):
    code: CaptureAlignmentReasonCode
    severity: CaptureAlignmentSeverity
    metric: str
    observed: float
    threshold: float
    comparison: str = ">"


class CaptureAlignmentResult(StrictModel):
    alignment_id: UUID
    source_frame_id: UUID
    calibration_id: UUID
    view: CaptureViewType
    policy_version: str
    verdict: CaptureAlignmentVerdict
    next_action: CaptureAlignmentAction
    metrics: CaptureAlignmentMetrics
    findings: list[CaptureAlignmentFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> "CaptureAlignmentResult":
        has_reject = any(item.severity is CaptureAlignmentSeverity.REJECT for item in self.findings)
        has_warn = any(item.severity is CaptureAlignmentSeverity.WARN for item in self.findings)
        expected_verdict = (
            CaptureAlignmentVerdict.REJECT
            if has_reject
            else CaptureAlignmentVerdict.WARN
            if has_warn
            else CaptureAlignmentVerdict.ACCEPT
        )
        if self.verdict is not expected_verdict:
            raise ValueError("alignment verdict must match finding severities")

        expected_action = (
            CaptureAlignmentAction.CONTINUE_CAPTURE_WORKFLOW
            if not self.findings
            else CaptureAlignmentService.action_for(self.findings[0].code)
        )
        if self.next_action is not expected_action:
            raise ValueError("alignment next_action must match the first finding")
        return self


class CaptureAlignmentService:
    """Read-only camera-tilt/perspective guidance from active calibration evidence."""

    _ACTIONS = {
        CaptureAlignmentReasonCode.CAMERA_TILT_RISK: CaptureAlignmentAction.REALIGN_CAMERA_PERPENDICULAR,
        CaptureAlignmentReasonCode.PERSPECTIVE_DISTORTION_RISK: CaptureAlignmentAction.REDUCE_PERSPECTIVE_DISTORTION,
    }

    def __init__(self, policy: CaptureAlignmentPolicy | None = None) -> None:
        self.policy = policy or CaptureAlignmentPolicy()

    def evaluate(
        self,
        session: CaptureSession,
        *,
        view: CaptureViewType,
    ) -> CaptureAlignmentResult:
        clean = active_clean_reference(session, view)
        if clean is None:
            raise CaptureAlignmentError(
                f"camera alignment requires an active clean reference for view {view.value}"
            )
        calibration = calibration_for_active_reference(session, view)
        if calibration is None:
            raise CaptureAlignmentError(
                f"camera alignment requires calibration for active clean reference {clean.frame_id}"
            )

        metrics = self._metrics(
            calibration.homography,
            width_px=clean.camera.width_px,
            height_px=clean.camera.height_px,
        )
        findings = self._findings(metrics)
        verdict = self._verdict(findings)
        action = (
            CaptureAlignmentAction.CONTINUE_CAPTURE_WORKFLOW
            if not findings
            else self.action_for(findings[0].code)
        )
        evidence_key = ",".join(f"{value:.17g}" for value in calibration.homography)
        alignment_id = uuid5(
            NAMESPACE_URL,
            "mrea:capture-alignment:v1:"
            f"{clean.frame_id}:{calibration.calibration_id}:"
            f"{clean.camera.width_px}x{clean.camera.height_px}:"
            f"{evidence_key}:{self.policy.policy_version}",
        )
        return CaptureAlignmentResult(
            alignment_id=alignment_id,
            source_frame_id=clean.frame_id,
            calibration_id=calibration.calibration_id,
            view=view,
            policy_version=self.policy.policy_version,
            verdict=verdict,
            next_action=action,
            metrics=metrics,
            findings=findings,
        )

    @classmethod
    def action_for(cls, code: CaptureAlignmentReasonCode) -> CaptureAlignmentAction:
        return cls._ACTIONS[code]

    @staticmethod
    def _metrics(
        homography: list[float],
        *,
        width_px: int,
        height_px: int,
    ) -> CaptureAlignmentMetrics:
        if len(homography) != 9 or not all(isfinite(value) for value in homography):
            raise CaptureAlignmentError("alignment requires a finite 3x3 homography")

        h00, h01, h02, h10, h11, h12, h20, h21, h22 = homography
        max_x = float(width_px - 1)
        max_y = float(height_px - 1)
        corners = ((0.0, 0.0), (max_x, 0.0), (max_x, max_y), (0.0, max_y))
        denominators = [h20 * x + h21 * y + h22 for x, y in corners]
        epsilon = 1e-12
        if any(abs(value) <= epsilon for value in denominators):
            raise CaptureAlignmentError("homography has a projective pole on the source frame boundary")
        positive = all(value > 0 for value in denominators)
        negative = all(value < 0 for value in denominators)
        if not (positive or negative):
            raise CaptureAlignmentError("homography denominator changes sign across the source frame")

        abs_denominators = [abs(value) for value in denominators]
        perspective_scale_ratio = max(abs_denominators) / min(abs_denominators)

        center_x = max_x / 2.0
        center_y = max_y / 2.0
        denominator = h20 * center_x + h21 * center_y + h22
        if abs(denominator) <= epsilon:
            raise CaptureAlignmentError("homography is singular at the source frame center")
        numerator_x = h00 * center_x + h01 * center_y + h02
        numerator_y = h10 * center_x + h11 * center_y + h12
        denominator_sq = denominator * denominator

        du_dx = (h00 * denominator - numerator_x * h20) / denominator_sq
        du_dy = (h01 * denominator - numerator_x * h21) / denominator_sq
        dv_dx = (h10 * denominator - numerator_y * h20) / denominator_sq
        dv_dy = (h11 * denominator - numerator_y * h21) / denominator_sq

        x_scale = hypot(du_dx, dv_dx)
        y_scale = hypot(du_dy, dv_dy)
        if x_scale <= epsilon or y_scale <= epsilon:
            raise CaptureAlignmentError("homography has a degenerate local mapping at the frame center")

        anisotropy = abs(x_scale - y_scale) / max(x_scale, y_scale)
        non_orthogonality = abs((du_dx * du_dy + dv_dx * dv_dy) / (x_scale * y_scale))
        camera_tilt_proxy = min(1.0, max(anisotropy, non_orthogonality))

        return CaptureAlignmentMetrics(
            camera_tilt_proxy=camera_tilt_proxy,
            perspective_scale_ratio=perspective_scale_ratio,
        )

    def _findings(self, metrics: CaptureAlignmentMetrics) -> list[CaptureAlignmentFinding]:
        findings: list[CaptureAlignmentFinding] = []
        if self.policy.check_camera_tilt:
            finding = self._high(
                CaptureAlignmentReasonCode.CAMERA_TILT_RISK,
                "camera_tilt_proxy",
                metrics.camera_tilt_proxy,
                self.policy.camera_tilt_warn_proxy,
                self.policy.camera_tilt_reject_proxy,
            )
            if finding is not None:
                findings.append(finding)
        if self.policy.check_perspective_distortion:
            finding = self._high(
                CaptureAlignmentReasonCode.PERSPECTIVE_DISTORTION_RISK,
                "perspective_scale_ratio",
                metrics.perspective_scale_ratio,
                self.policy.perspective_warn_scale_ratio,
                self.policy.perspective_reject_scale_ratio,
            )
            if finding is not None:
                findings.append(finding)
        return findings

    @staticmethod
    def _high(
        code: CaptureAlignmentReasonCode,
        metric: str,
        observed: float,
        warn: float,
        reject: float,
    ) -> CaptureAlignmentFinding | None:
        if observed > reject:
            return CaptureAlignmentFinding(
                code=code,
                severity=CaptureAlignmentSeverity.REJECT,
                metric=metric,
                observed=observed,
                threshold=reject,
            )
        if observed > warn:
            return CaptureAlignmentFinding(
                code=code,
                severity=CaptureAlignmentSeverity.WARN,
                metric=metric,
                observed=observed,
                threshold=warn,
            )
        return None

    @staticmethod
    def _verdict(findings: list[CaptureAlignmentFinding]) -> CaptureAlignmentVerdict:
        if any(item.severity is CaptureAlignmentSeverity.REJECT for item in findings):
            return CaptureAlignmentVerdict.REJECT
        return CaptureAlignmentVerdict.WARN if findings else CaptureAlignmentVerdict.ACCEPT


class RussianCaptureAlignmentGuidanceAdapter:
    _MESSAGES = {
        CaptureAlignmentReasonCode.CAMERA_TILT_RISK: (
            "Камера заметно наклонена относительно Measurement Mat: выровняйте её ближе к перпендикуляру к рабочей плоскости."
        ),
        CaptureAlignmentReasonCode.PERSPECTIVE_DISTORTION_RISK: (
            "Перспективное искажение слишком велико: центрируйте камеру над Measurement Mat и снимайте плоскость более фронтально."
        ),
    }

    @classmethod
    def messages(cls, result: CaptureAlignmentResult) -> list[str]:
        if not result.findings:
            return ["Положение камеры пригодно для продолжения capture workflow."]
        return [cls._MESSAGES[item.code] for item in result.findings]
