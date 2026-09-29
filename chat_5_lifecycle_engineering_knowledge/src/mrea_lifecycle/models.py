from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping, Optional, Tuple


class LifecycleEventType(str, Enum):
    """Internal Chat 5 event vocabulary; not a shared contract enum."""

    REVISION_CREATED = "REVISION_CREATED"
    MANUFACTURED = "MANUFACTURED"
    INSTALLED = "INSTALLED"
    TESTED = "TESTED"
    FAILED = "FAILED"


class LifecycleState(str, Enum):
    """Revision-level internal projection; not a shared contract."""

    DRAFT = "DRAFT"
    MANUFACTURED = "MANUFACTURED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


class RevisionOrigin(str, Enum):
    """Internal provenance for how a lifecycle revision entered Chat 5."""

    MANUAL = "MANUAL"
    CAD_TRANSFER = "CAD_TRANSFER"


class CADVerificationStatus(str, Enum):
    """Internal snapshot of canonical CADVerificationReport.overall_status."""

    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class PhysicalPartState(str, Enum):
    """Internal state of one real manufactured part instance."""

    MANUFACTURED = "MANUFACTURED"
    INSTALLED = "INSTALLED"
    TESTED = "TESTED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    REMOVED = "REMOVED"
    SUPERSEDED = "SUPERSEDED"


class PhysicalLifecycleEventType(str, Enum):
    """Internal physical-instance event vocabulary; never exported as LifecycleEvent v1."""

    MANUFACTURED = "MANUFACTURED"
    INSTALLED = "INSTALLED"
    TESTED = "TESTED"
    ACTIVATED = "ACTIVATED"
    FAILED = "FAILED"
    REMOVED = "REMOVED"
    SUPERSEDED = "SUPERSEDED"


class PhysicalTestOutcome(str, Enum):
    """Explicit result used by the physical-instance activation gate."""

    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CADArtifactReference:
    """Internal snapshot of a canonical ArtifactReference from CADPackage."""

    artifact_id: str
    kind: str
    uri: str
    media_type: Optional[str] = None
    sha256: Optional[str] = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CADRevisionLink:
    """Traceability retained when a Revision is prepared from canonical CAD output."""

    cad_package_id: str
    sketch_package_id: str
    cad_verification_report_id: str
    cad_adapter: str
    verification_status: CADVerificationStatus
    artifacts: Tuple[CADArtifactReference, ...] = ()


@dataclass(frozen=True, slots=True)
class Revision:
    revision_id: str
    part_id: str
    revision_code: str
    created_at: datetime
    parent_revision_id: Optional[str] = None
    notes: Optional[str] = None
    source_cad_artifact_id: Optional[str] = None
    origin: RevisionOrigin = RevisionOrigin.MANUAL
    cad_link: Optional[CADRevisionLink] = None


@dataclass(frozen=True, slots=True)
class ManufacturingRecord:
    manufacturing_id: str
    revision_id: str
    material: str
    method: str
    manufactured_at: datetime
    batch: Optional[str] = None
    machine: Optional[str] = None
    print_profile: Optional[str] = None
    contractor: Optional[str] = None
    cost: Optional[Decimal] = None
    post_processing: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PhysicalPartInstance:
    """Identity snapshot for one real item produced by one manufacturing record."""

    instance_id: str
    part_id: str
    revision_id: str
    manufacturing_id: str
    material: str
    method: str
    manufactured_at: datetime
    batch: Optional[str] = None
    machine: Optional[str] = None
    print_profile: Optional[str] = None


@dataclass(frozen=True, slots=True)
class Installation:
    installation_id: str
    revision_id: str
    manufacturing_id: str
    equipment_id: str
    position: str
    installed_at: datetime
    technician: Optional[str] = None
    notes: Optional[str] = None
    instance_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TestRecord:
    test_id: str
    revision_id: str
    tested_at: datetime
    test_type: str
    conditions: str
    result: str
    conclusion: str
    manufacturing_id: Optional[str] = None
    installation_id: Optional[str] = None
    artifact_ids: Tuple[str, ...] = ()
    instance_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class FailureRecord:
    failure_id: str
    revision_id: str
    failed_at: datetime
    failure_type: str
    damage_location: str
    circumstances: str
    evidence_artifact_ids: Tuple[str, ...]
    manufacturing_id: Optional[str] = None
    installation_id: Optional[str] = None
    estimated_cause: Optional[str] = None
    confirmed_cause: Optional[str] = None
    related_feature: Optional[str] = None
    instance_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    event_id: str
    event_type: LifecycleEventType
    occurred_at: datetime
    sequence: int
    revision_id: str
    manufacturing_id: Optional[str] = None
    installation_id: Optional[str] = None
    test_id: Optional[str] = None
    failure_id: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PhysicalLifecycleEvent:
    """Internal event for one concrete manufactured instance."""

    event_id: str
    event_type: PhysicalLifecycleEventType
    occurred_at: datetime
    sequence: int
    instance_id: str
    revision_id: str
    manufacturing_id: str
    installation_id: Optional[str] = None
    test_id: Optional[str] = None
    failure_id: Optional[str] = None
    equipment_id: Optional[str] = None
    position: Optional[str] = None
    test_outcome: Optional[PhysicalTestOutcome] = None
    replacement_instance_id: Optional[str] = None
    notes: Optional[str] = None
