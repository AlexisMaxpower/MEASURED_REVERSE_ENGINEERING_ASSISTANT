from mrea_capture.models import CaptureViewType
from mrea_capture.preparation import (
    CapturePreparationAction,
    CapturePreparationCheckCode,
    CapturePreparationFindingStatus,
    CapturePreparationObservation,
    CapturePreparationPolicy,
    CapturePreparationService,
    RussianCapturePreparationGuidanceAdapter,
)


def _ready_observation() -> CapturePreparationObservation:
    return CapturePreparationObservation(
        view=CaptureViewType.FRONT,
        measurement_mat_ready=True,
        object_stable=True,
        background_clear=True,
        lighting_usable=True,
        features_unobstructed=True,
    )


def test_ready_preparation_allows_clean_reference_capture() -> None:
    result = CapturePreparationService().evaluate(_ready_observation())

    assert result.ready is True
    assert result.next_action is CapturePreparationAction.CAPTURE_CLEAN_REFERENCE
    assert result.findings == []
    assert result.policy_version == "chat1.capture-preparation.v1"


def test_preparation_fails_closed_and_keeps_deterministic_priority() -> None:
    observation = CapturePreparationObservation(
        view=CaptureViewType.FRONT,
        measurement_mat_ready=None,
        object_stable=False,
        background_clear=False,
        lighting_usable=True,
        features_unobstructed=None,
    )

    result = CapturePreparationService().evaluate(observation)

    assert result.ready is False
    assert result.next_action is CapturePreparationAction.FIX_MEASUREMENT_MAT
    assert [finding.code for finding in result.findings] == [
        CapturePreparationCheckCode.MEASUREMENT_MAT_READY,
        CapturePreparationCheckCode.OBJECT_STABLE,
        CapturePreparationCheckCode.BACKGROUND_CLEAR,
        CapturePreparationCheckCode.FEATURES_UNOBSTRUCTED,
    ]
    assert [finding.status for finding in result.findings] == [
        CapturePreparationFindingStatus.UNKNOWN,
        CapturePreparationFindingStatus.FAILED,
        CapturePreparationFindingStatus.FAILED,
        CapturePreparationFindingStatus.UNKNOWN,
    ]


def test_policy_can_make_a_preparation_check_non_blocking() -> None:
    observation = CapturePreparationObservation(
        view=CaptureViewType.DETAIL_A,
        measurement_mat_ready=True,
        object_stable=True,
        background_clear=None,
        lighting_usable=True,
        features_unobstructed=True,
    )
    service = CapturePreparationService(
        CapturePreparationPolicy(require_background_clear=False)
    )

    result = service.evaluate(observation)

    assert result.ready is True
    assert result.next_action is CapturePreparationAction.CAPTURE_CLEAN_REFERENCE
    assert result.findings == []


def test_preparation_evaluation_is_pure_and_deterministic() -> None:
    observation = CapturePreparationObservation(
        view=CaptureViewType.LEFT,
        measurement_mat_ready=True,
        object_stable=False,
        background_clear=True,
        lighting_usable=True,
        features_unobstructed=True,
    )
    before = observation.model_dump(mode="json")
    service = CapturePreparationService()

    first = service.evaluate(observation)
    second = service.evaluate(observation)

    assert first == second
    assert observation.model_dump(mode="json") == before
    assert first.next_action is CapturePreparationAction.STABILIZE_OBJECT


def test_russian_guidance_is_actionable_for_failed_and_unknown_checks() -> None:
    result = CapturePreparationService().evaluate(
        CapturePreparationObservation(
            view=CaptureViewType.TOP,
            measurement_mat_ready=True,
            object_stable=True,
            background_clear=False,
            lighting_usable=None,
            features_unobstructed=True,
        )
    )

    messages = RussianCapturePreparationGuidanceAdapter.messages(result)

    assert messages == [
        "Уберите лишние предметы и контрастные помехи из рабочей области вокруг детали.",
        "Подтвердите, что освещение равномерное и не создаёт мешающих бликов или теней.",
    ]


def test_ready_guidance_has_single_capture_instruction() -> None:
    result = CapturePreparationService().evaluate(_ready_observation())

    assert RussianCapturePreparationGuidanceAdapter.messages(result) == [
        "Подготовка завершена: можно снимать clean-reference кадр."
    ]
