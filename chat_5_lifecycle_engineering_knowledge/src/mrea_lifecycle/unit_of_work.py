from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, cast

from .physical import PhysicalPartLifecycleService
from .repository import LifecycleRepository
from .services import (
    CADRevisionPreparationService,
    FailureService,
    InstallationService,
    ManufacturingService,
    RevisionService,
    TestService,
)
from .store import InMemoryLifecycleStore


class LifecycleUnitOfWork:
    """Transactional application boundary spanning canonical and physical writes."""

    def __init__(self, repository: LifecycleRepository) -> None:
        self.repository = repository
        # Existing services are structurally repository-based at runtime. The cast keeps
        # their legacy concrete annotation backward compatible until a later cleanup pass.
        store = cast(InMemoryLifecycleStore, repository)
        self.revisions = RevisionService(store)
        self.cad_revisions = CADRevisionPreparationService(store)
        self.manufacturing = ManufacturingService(store)
        self.installations = InstallationService(store)
        self.tests = TestService(store)
        self.failures = FailureService(store)
        self.physical = PhysicalPartLifecycleService(store)

    @contextmanager
    def transaction(self) -> Iterator[LifecycleUnitOfWork]:
        with self.repository.transaction():
            yield self
