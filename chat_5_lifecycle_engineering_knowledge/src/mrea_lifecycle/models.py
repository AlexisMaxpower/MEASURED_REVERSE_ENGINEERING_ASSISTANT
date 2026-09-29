from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple


class LifecycleEventType(str, Enum):
    """Internal Chat 5 event vocabulary; not a shared contract enum."""

    REVISION_CREATED = "REVISION_CREATED"
    MANUFACTURED = "MANUFACTURED"
    INSTALLED = "INSTALLED"
    TESTED = "TESTED"
    FAILED = "FAILED"


class LifecycleState(str, Enum):
    """Internal projection; not a shared contract."""

    DRAFT = "DRAFT"
    MANUFACTURED = "MANUFACTURED"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Revision:
    revision_id: str
    part_id: str
    revision_code: str
    created_at: datetime
    parent_revision_id: Optional[str] = None
    notes: Optional[str] = None
    source_cad_artifact_id: Optional[str] = None


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
class Installation:
    installation_id: str
    revision_id: str
    manufacturing_id: str
    equipment_id: str
    position: str
    installed_at: datetime
    technician: Optional[str] = None
    notes: Optional[str] = None


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
