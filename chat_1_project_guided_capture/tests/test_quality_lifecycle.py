from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from mrea_capture.artifacts import FileSystemArtifactStore
from mrea_capture.contracts import CanonicalContractBuilder
from mrea_capture.models import (
    CalibrationResult,
    CameraMetadata,
    CaptureQualityFinding,
    CaptureQualityMetrics,
    CaptureQualityResult,
    CaptureQualityVerdict,
    CaptureViewStatus,
    CaptureViewType,
    MeasurementMatProfile,
    PartContext,
    Project,
    QualityReasonCode,
    QualitySeverity,
)
from mrea_capture.quality_lifecycle import (
    CaptureQualityLifecycleError,
    CaptureQualityLifecycleService,
)
from mrea_capture.repositories import JsonCaptureSessionRepository
from mrea_capture.services import CapturePlanService, CaptureSessionService


class StubAnalyzer:
    def __init__(self, verdict: CaptureQualityVerdict) -> None:
        self._verdict = verdict

    def analyze(
        self,
        image_bytes: bytes,
        *,
        source_frame_id: UUID,
        view: CaptureViewType,
        calibration: CalibrationResult | None = None,
        mat_profile: MeasurementMatProfile | None = None,
    ) -> CaptureQualityResult:
        del image_bytes
        finding: CaptureQualityFinding | None = None
        if self._verdict is CaptureQualityVerdict.WARN:
            finding = CaptureQualityFinding(
                code=QualityReasonCode.GLARE_RISK,
                severity=QualitySeverity.WARN,
                metric="glare_proxy_fraction",
                observed=0.01,
                threshold=0.005,
                comparison=">",
            )
        elif self._verdict is CaptureQualityVerdict.REJECT:
            finding = CaptureQualityFinding(
                code=QualityReasonCode.BLUR,
                severity=QualitySeverity.REJECT,
                metric="laplacian_variance",
                observed=5.0,
                threshold=20.0,
                comparison="<",
            )

        return CaptureQualityResult(
            analysis_id=uuid5(
                NAMESPACE_URL,
                f"mrea:test-quality:{source_frame_id}:{self._verdict.value}",
            ),
            source_frame_id=source_frame_id,
            view=view,
            calibration_id=calibration.calibration_id if calibration else None,
            mat_id=(
                mat_profile.mat_id
                if mat_profile is not None
                else calibration.mat_id
                if calibration is not None
                else None
            ),
            policy_version="test.capture-quality.v1",
            verdict=self._verdict,
            metrics=CaptureQualityMetrics(
                laplacian_variance=100.0,
                mean_luma=128.0,
                dark_clipped_fraction=0.0,
                bright_clipped_fraction=0.0,
                glare_proxy_fraction=0.0,
                edge_density=0.1,
                border_edge_ratio=0.1,
                marker_corner_visibility=None,
            ),
            findings=[finding] if finding is not None else [],
        )


def _fixture(tmp_path: Path, verdict: CaptureQualityVerdict):
    project = Project(name="Quality lifecycle", part=PartContext(part_type="test part"))
    plan = CapturePlanService().create_plan(project)
    repository = JsonCaptureSessionRepository(tmp_path)
    store = FileSystemArtifactStore(tmp_path)
    capture = CaptureSessionService(repository, store)
    session = capture.start(plan)
    capture.capture_clean_reference(
        session.session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"immutable-clean-reference",
        camera=CameraMetadata(width_px=640, height_px=480),
    )
    lifecycle = CaptureQualityLifecycleService(
        repository,
        store,
        StubAnalyzer(verdict),
    )
    return project, repository, capture, lifecycle, session.session_id


@pytest.mark.parametrize(
    ("verdict", "expected_status"),
    [
        (CaptureQualityVerdict.ACCEPT, CaptureViewStatus.CAPTURED),
        (CaptureQualityVerdict.WARN, CaptureViewStatus.CAPTURED),
        (CaptureQualityVerdict.REJECT, CaptureViewStatus.IN_PROGRESS),
    ],
)
def test_quality_verdict_synchronizes_internal_view_status_without_contract_delta(
    tmp_path: Path,
    verdict: CaptureQualityVerdict,
    expected_status: CaptureViewStatus,
) -> None:
    project, repository, capture, lifecycle, session_id = _fixture(tmp_path, verdict)
    before = CanonicalContractBuilder.capture_package(project, capture.get(session_id))

    result = lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)
    restored = capture.get(session_id)
    after = CanonicalContractBuilder.capture_package(project, restored)

    assert result.verdict is verdict
    assert restored.views[0].status is expected_status
    assert before == after
    assert len(restored.quality_analyses) == 1


def test_reject_blocks_quality_aware_accept_until_new_clean_attempt_passes(
    tmp_path: Path,
) -> None:
    _, repository, capture, lifecycle, session_id = _fixture(
        tmp_path,
        CaptureQualityVerdict.REJECT,
    )
    lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)

    with pytest.raises(CaptureQualityLifecycleError, match="quality is REJECT"):
        lifecycle.accept_view(session_id, view=CaptureViewType.FRONT)

    new_frame = capture.recapture_clean_reference(
        session_id,
        view=CaptureViewType.FRONT,
        image_bytes=b"new-immutable-clean-reference",
        camera=CameraMetadata(width_px=640, height_px=480),
    )
    recaptured = capture.get(session_id)
    assert recaptured.views[0].status is CaptureViewStatus.CAPTURED
    assert recaptured.views[0].active_clean_reference_frame_id == new_frame.frame_id

    passing = CaptureQualityLifecycleService(
        repository,
        FileSystemArtifactStore(tmp_path),
        StubAnalyzer(CaptureQualityVerdict.ACCEPT),
    )
    passing.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)
    accepted = passing.accept_view(session_id, view=CaptureViewType.FRONT)

    assert accepted.views[0].status is CaptureViewStatus.ACCEPTED
    assert len(accepted.quality_analyses) == 2


def test_repeated_analysis_repairs_status_from_persisted_quality_evidence(
    tmp_path: Path,
) -> None:
    _, repository, capture, lifecycle, session_id = _fixture(
        tmp_path,
        CaptureQualityVerdict.REJECT,
    )
    first = lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)

    stale = repository.get(session_id)
    stale.views[0].status = CaptureViewStatus.CAPTURED
    repository.save(stale)

    second = lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)
    repaired = capture.get(session_id)

    assert second == first
    assert repaired.views[0].status is CaptureViewStatus.IN_PROGRESS
    assert len(repaired.quality_analyses) == 1


def test_accepted_view_requires_explicit_reopen_before_quality_reanalysis(
    tmp_path: Path,
) -> None:
    _, _, _, lifecycle, session_id = _fixture(
        tmp_path,
        CaptureQualityVerdict.ACCEPT,
    )
    lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)
    lifecycle.accept_view(session_id, view=CaptureViewType.FRONT)

    with pytest.raises(CaptureQualityLifecycleError, match="must be reopened"):
        lifecycle.analyze_clean_reference(session_id, view=CaptureViewType.FRONT)
