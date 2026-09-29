"""Chat 1 domain/application baseline for MREA Project & Guided Capture."""

from .artifacts import ArtifactNotFoundError, FileSystemArtifactStore
from .calibration import (
    CalibrationDetectionError,
    CalibrationService,
    OpenCvCharucoCalibrationDetector,
)
from .contracts import CanonicalContractBuilder, CanonicalContractError
from .models import (
    ArtifactRecord,
    CalibrationResult,
    CameraMetadata,
    CapturePlan,
    CapturePlanItem,
    CaptureSession,
    CaptureViewProgress,
    CaptureViewStatus,
    CaptureViewType,
    FrameKind,
    FrameRecord,
    MeasurementMatProfile,
    PartContext,
    Project,
    ProjectStatus,
    RectifiedReferenceRecord,
)
from .rectification import (
    OpenCvPerspectiveNormalizer,
    PerspectiveNormalizer,
    RectificationError,
    RectificationService,
    RectifiedRaster,
)
from .repositories import (
    CaptureSessionNotFoundError,
    JsonCaptureSessionRepository,
    JsonProjectRepository,
    ProjectNotFoundError,
)
from .services import (
    CapturePlanService,
    CaptureSessionService,
    CaptureWorkflowError,
    ProjectService,
)

__all__ = [
    "ArtifactNotFoundError",
    "ArtifactRecord",
    "CalibrationDetectionError",
    "CalibrationResult",
    "CalibrationService",
    "CameraMetadata",
    "CanonicalContractBuilder",
    "CanonicalContractError",
    "CapturePlan",
    "CapturePlanItem",
    "CapturePlanService",
    "CaptureSession",
    "CaptureSessionNotFoundError",
    "CaptureSessionService",
    "CaptureViewProgress",
    "CaptureViewStatus",
    "CaptureViewType",
    "CaptureWorkflowError",
    "FileSystemArtifactStore",
    "FrameKind",
    "FrameRecord",
    "JsonCaptureSessionRepository",
    "JsonProjectRepository",
    "MeasurementMatProfile",
    "OpenCvCharucoCalibrationDetector",
    "OpenCvPerspectiveNormalizer",
    "PartContext",
    "PerspectiveNormalizer",
    "Project",
    "ProjectNotFoundError",
    "ProjectService",
    "ProjectStatus",
    "RectificationError",
    "RectificationService",
    "RectifiedRaster",
    "RectifiedReferenceRecord",
]
