from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from .models import (
    CapturePlan,
    CapturePlanItem,
    CaptureSession,
    CaptureViewProgress,
    CaptureViewType,
    PartContext,
    Project,
    utc_now,
)
from .repositories import ProjectRepository


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def create_project(self, *, name: str, part: PartContext) -> Project:
        project = Project(name=name, part=part)
        self._repository.save(project)
        return project

    def get_project(self, project_id: UUID) -> Project:
        return self._repository.get(project_id)

    def archive_project(self, project_id: UUID, *, now: datetime | None = None) -> Project:
        project = self._repository.get(project_id)
        project.status = "ARCHIVED"
        project.updated_at = now or utc_now()
        self._repository.save(project)
        return project


class CapturePlanService:
    """Build deterministic local capture plans.

    FRONT is the only implicit baseline view because SSOT explicitly requires the
    FRONT view to be completable. Extra views must be requested explicitly until
    Integrator/product policy defines a canonical recommendation strategy.
    """

    _RATIONALE = {
        CaptureViewType.FRONT: "Baseline orthographic reference required by Chat 1 acceptance criteria.",
        CaptureViewType.LEFT: "User-requested left-side coverage.",
        CaptureViewType.RIGHT: "User-requested right-side coverage.",
        CaptureViewType.TOP: "User-requested top coverage.",
        CaptureViewType.BOTTOM: "User-requested bottom coverage.",
        CaptureViewType.REAR: "User-requested rear coverage.",
        CaptureViewType.DETAIL_A: "User-requested detail coverage A.",
        CaptureViewType.DETAIL_B: "User-requested detail coverage B.",
        CaptureViewType.OPTIONAL_3Q: "Optional three-quarter context view.",
    }

    def create_plan(
        self,
        project: Project,
        *,
        views: Iterable[CaptureViewType] | None = None,
    ) -> CapturePlan:
        requested = list(views) if views is not None else [CaptureViewType.FRONT]
        if not requested:
            requested = [CaptureViewType.FRONT]

        ordered_unique: list[CaptureViewType] = []
        seen: set[CaptureViewType] = set()
        for view in requested:
            if view not in seen:
                ordered_unique.append(view)
                seen.add(view)

        items = [
            CapturePlanItem(
                sequence=index,
                view=view,
                required=view is not CaptureViewType.OPTIONAL_3Q,
                rationale=self._RATIONALE[view],
            )
            for index, view in enumerate(ordered_unique, start=1)
        ]
        return CapturePlan(project_id=project.project_id, items=items)

    def start_session(self, plan: CapturePlan) -> CaptureSession:
        return CaptureSession(
            project_id=plan.project_id,
            plan_id=plan.plan_id,
            views=[CaptureViewProgress(view=item.view) for item in plan.items],
        )
