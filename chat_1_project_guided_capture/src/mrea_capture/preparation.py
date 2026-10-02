from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .models import CameraMetadata, CaptureViewType, FrameRecord, StrictModel
from .services import CaptureSessionService


class CapturePreparationCheckCode(StrEnum):
    MEASUREMENT_MAT_READY = "MEASUREMENT_MAT_READY"
    OBJECT_STABLE = "OBJECT_STABLE"
    BACKGROUND_CLEAR = "BACKGROUND_CLEAR"
    LIGHTING_USABLE = "LIGHTING_USABLE"
    FEATURES_UNOBSTRUCTED = "FEATURES_UNOBSTRUCTED"


class CapturePreparationFindingStatus(StrEnum):
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class CapturePreparationAction(StrEnum):
    FIX_MEASUREMENT_MAT = "FIX_MEASUREMENT_MAT"
    STABILIZE_OBJECT = "STABILIZE_OBJECT"
    CLEAR_BACKGROUND = "CLEAR_BACKGROUND"
    ADJUST_LIGHTING = "ADJUST_LIGHTING"
    REMOVE_OCCLUSIONS = "REMOVE_OCCLUSIONS"
    CAPTURE_CLEAN_REFERENCE = "CAPTURE_CLEAN_REFERENCE"


class CapturePreparationObservation(StrictModel):
    """Operator-observed pre-capture setup state; never metrology truth."""

    view: CaptureViewType
    measurement_mat_ready: bool | None = None
    object_stable: bool | None = None
    background_clear: bool | None = None
    lighting_usable: bool | None = None
    features_unobstructed: bool | None = None


class CapturePreparationPolicy(StrictModel):
    policy_version: str = "chat1.capture-preparation.v1"
    require_measurement_mat_ready: bool = True
    require_object_stable: bool = True
    require_background_clear: bool = True
    require_lighting_usable: bool = True
    require_features_unobstructed: bool = True


class CapturePreparationFinding(StrictModel):
    code: CapturePreparationCheckCode
    status: CapturePreparationFindingStatus


class CapturePreparationResult(StrictModel):
    view: CaptureViewType
    policy_version: str
    ready: bool
    next_action: CapturePreparationAction
    findings: list[CapturePreparationFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_state(self) -> "CapturePreparationResult":
        expected_ready = not self.findings
        if self.ready is not expected_ready:
            raise ValueError("preparation ready state must match findings")
        expected_action = (
            CapturePreparationAction.CAPTURE_CLEAN_REFERENCE
            if expected_ready
            else CapturePreparationService.action_for(self.findings[0].code)
        )
        if self.next_action is not expected_action:
            raise ValueError("preparation next_action must match the first finding")
        return self


class CapturePreparationService:
    """Fail-closed, deterministic setup guidance before clean-reference capture."""

    _CHECKS = (
        (
            "measurement_mat_ready",
            "require_measurement_mat_ready",
            CapturePreparationCheckCode.MEASUREMENT_MAT_READY,
        ),
        (
            "object_stable",
            "require_object_stable",
            CapturePreparationCheckCode.OBJECT_STABLE,
        ),
        (
            "background_clear",
            "require_background_clear",
            CapturePreparationCheckCode.BACKGROUND_CLEAR,
        ),
        (
            "lighting_usable",
            "require_lighting_usable",
            CapturePreparationCheckCode.LIGHTING_USABLE,
        ),
        (
            "features_unobstructed",
            "require_features_unobstructed",
            CapturePreparationCheckCode.FEATURES_UNOBSTRUCTED,
        ),
    )

    _ACTIONS = {
        CapturePreparationCheckCode.MEASUREMENT_MAT_READY: CapturePreparationAction.FIX_MEASUREMENT_MAT,
        CapturePreparationCheckCode.OBJECT_STABLE: CapturePreparationAction.STABILIZE_OBJECT,
        CapturePreparationCheckCode.BACKGROUND_CLEAR: CapturePreparationAction.CLEAR_BACKGROUND,
        CapturePreparationCheckCode.LIGHTING_USABLE: CapturePreparationAction.ADJUST_LIGHTING,
        CapturePreparationCheckCode.FEATURES_UNOBSTRUCTED: CapturePreparationAction.REMOVE_OCCLUSIONS,
    }

    def __init__(self, policy: CapturePreparationPolicy | None = None) -> None:
        self.policy = policy or CapturePreparationPolicy()

    def evaluate(self, observation: CapturePreparationObservation) -> CapturePreparationResult:
        findings: list[CapturePreparationFinding] = []
        for observation_field, policy_field, code in self._CHECKS:
            if not getattr(self.policy, policy_field):
                continue
            value = getattr(observation, observation_field)
            if value is True:
                continue
            findings.append(
                CapturePreparationFinding(
                    code=code,
                    status=(
                        CapturePreparationFindingStatus.UNKNOWN
                        if value is None
                        else CapturePreparationFindingStatus.FAILED
                    ),
                )
            )

        return CapturePreparationResult(
            view=observation.view,
            policy_version=self.policy.policy_version,
            ready=not findings,
            next_action=(
                CapturePreparationAction.CAPTURE_CLEAN_REFERENCE
                if not findings
                else self.action_for(findings[0].code)
            ),
            findings=findings,
        )

    @classmethod
    def action_for(cls, code: CapturePreparationCheckCode) -> CapturePreparationAction:
        return cls._ACTIONS[code]


class CapturePreparationGateError(RuntimeError):
    """Raised before any capture mutation when required setup evidence is not ready."""

    def __init__(self, result: CapturePreparationResult) -> None:
        self.result = result
        first = result.findings[0]
        super().__init__(
            f"capture preparation blocked for {result.view.value}: "
            f"{first.code.value}/{first.status.value}"
        )


class PreparedCleanReferenceCapture(StrictModel):
    """Ephemeral application result coupling preflight outcome to the captured frame."""

    preparation: CapturePreparationResult
    frame: FrameRecord


class CapturePreparationCaptureService:
    """Application facade that enforces preparation before clean-reference mutation."""

    def __init__(
        self,
        capture_service: CaptureSessionService,
        preparation_service: CapturePreparationService | None = None,
    ) -> None:
        self._capture_service = capture_service
        self._preparation_service = preparation_service or CapturePreparationService()

    def capture_clean_reference(
        self,
        session_id: UUID,
        *,
        observation: CapturePreparationObservation,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None = None,
        media_type: str = "image/jpeg",
        extension: str = ".jpg",
    ) -> PreparedCleanReferenceCapture:
        preparation = self._require_ready(observation)
        frame = self._capture_service.capture_clean_reference(
            session_id,
            view=observation.view,
            image_bytes=image_bytes,
            camera=camera,
            captured_at=captured_at,
            media_type=media_type,
            extension=extension,
        )
        return PreparedCleanReferenceCapture(preparation=preparation, frame=frame)

    def recapture_clean_reference(
        self,
        session_id: UUID,
        *,
        observation: CapturePreparationObservation,
        image_bytes: bytes,
        camera: CameraMetadata,
        captured_at: datetime | None = None,
        media_type: str = "image/jpeg",
        extension: str = ".jpg",
    ) -> PreparedCleanReferenceCapture:
        preparation = self._require_ready(observation)
        frame = self._capture_service.recapture_clean_reference(
            session_id,
            view=observation.view,
            image_bytes=image_bytes,
            camera=camera,
            captured_at=captured_at,
            media_type=media_type,
            extension=extension,
        )
        return PreparedCleanReferenceCapture(preparation=preparation, frame=frame)

    def _require_ready(
        self,
        observation: CapturePreparationObservation,
    ) -> CapturePreparationResult:
        result = self._preparation_service.evaluate(observation)
        if not result.ready:
            raise CapturePreparationGateError(result)
        return result


class RussianCapturePreparationGuidanceAdapter:
    _FAILED = {
        CapturePreparationCheckCode.MEASUREMENT_MAT_READY: "Выровняйте Measurement Mat и убедитесь, что его рабочая область и маркеры видны в кадре.",
        CapturePreparationCheckCode.OBJECT_STABLE: "Зафиксируйте деталь: она не должна смещаться во время серии кадров.",
        CapturePreparationCheckCode.BACKGROUND_CLEAR: "Уберите лишние предметы и контрастные помехи из рабочей области вокруг детали.",
        CapturePreparationCheckCode.LIGHTING_USABLE: "Настройте равномерный свет без резких теней и прямых бликов на детали.",
        CapturePreparationCheckCode.FEATURES_UNOBSTRUCTED: "Освободите измеряемые кромки, отверстия и другие важные признаки от перекрытий.",
    }
    _UNKNOWN = {
        CapturePreparationCheckCode.MEASUREMENT_MAT_READY: "Подтвердите, что Measurement Mat лежит ровно и его рабочая область видна.",
        CapturePreparationCheckCode.OBJECT_STABLE: "Подтвердите, что деталь надёжно зафиксирована.",
        CapturePreparationCheckCode.BACKGROUND_CLEAR: "Подтвердите, что фон вокруг детали очищен от лишних объектов.",
        CapturePreparationCheckCode.LIGHTING_USABLE: "Подтвердите, что освещение равномерное и не создаёт мешающих бликов или теней.",
        CapturePreparationCheckCode.FEATURES_UNOBSTRUCTED: "Подтвердите, что важные признаки детали ничем не перекрыты.",
    }

    @classmethod
    def messages(cls, result: CapturePreparationResult) -> list[str]:
        if result.ready:
            return ["Подготовка завершена: можно снимать clean-reference кадр."]
        messages: list[str] = []
        for finding in result.findings:
            source = cls._UNKNOWN if finding.status is CapturePreparationFindingStatus.UNKNOWN else cls._FAILED
            messages.append(source[finding.code])
        return messages
