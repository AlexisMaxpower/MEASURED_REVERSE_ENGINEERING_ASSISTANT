from __future__ import annotations

from contextlib import AbstractContextManager
from typing import List, MutableMapping, Protocol

from .models import (
    FailureRecord,
    Installation,
    LifecycleEvent,
    ManufacturingRecord,
    PhysicalLifecycleEvent,
    PhysicalPartInstance,
    Revision,
    TestRecord,
)


class LifecycleRepository(Protocol):
    """Internal persistence port for Chat 5 lifecycle application code."""

    revisions: MutableMapping[str, Revision]
    manufacturing_records: MutableMapping[str, ManufacturingRecord]
    installations: MutableMapping[str, Installation]
    tests: MutableMapping[str, TestRecord]
    failures: MutableMapping[str, FailureRecord]
    events: List[LifecycleEvent]
    physical_instances: MutableMapping[str, PhysicalPartInstance]
    physical_events: List[PhysicalLifecycleEvent]

    @property
    def transaction_depth(self) -> int: ...

    def transaction(self) -> AbstractContextManager[LifecycleRepository]: ...
