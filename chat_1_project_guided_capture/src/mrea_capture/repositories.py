from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol
from uuid import UUID

from .models import Project


class ProjectNotFoundError(LookupError):
    pass


class ProjectRepository(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: UUID) -> Project: ...


class JsonProjectRepository:
    """Local offline-first project persistence owned by Chat 1.

    This is an internal repository implementation, not a shared MREA contract.
    Files are written atomically to avoid exposing partially-written JSON.
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._projects_dir = self._root / "projects"
        self._projects_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, project_id: UUID) -> Path:
        return self._projects_dir / f"{project_id}.json"

    def save(self, project: Project) -> None:
        target = self._path_for(project.project_id)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            project.model_dump_json(indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, target)

    def get(self, project_id: UUID) -> Project:
        path = self._path_for(project_id)
        if not path.exists():
            raise ProjectNotFoundError(f"project not found: {project_id}")
        return Project.model_validate_json(path.read_text(encoding="utf-8"))
