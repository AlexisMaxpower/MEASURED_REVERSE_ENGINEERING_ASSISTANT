from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol
from uuid import UUID

from .models import CaptureSession, Project


class ProjectNotFoundError(LookupError):
    pass


class CaptureSessionNotFoundError(LookupError):
    pass


class ProjectRepository(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: UUID) -> Project: ...


class CaptureSessionRepository(Protocol):
    def save(self, session: CaptureSession) -> None: ...

    def get(self, session_id: UUID) -> CaptureSession: ...


class _AtomicJsonRepository:
    def __init__(self, root: Path | str, directory: str) -> None:
        self._directory = Path(root) / directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, record_id: UUID) -> Path:
        return self._directory / f"{record_id}.json"

    def _write_text_atomic(self, target: Path, content: str) -> None:
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, target)


class JsonProjectRepository(_AtomicJsonRepository):
    """Local offline-first project persistence owned by Chat 1."""

    def __init__(self, root: Path | str) -> None:
        super().__init__(root, "projects")

    def save(self, project: Project) -> None:
        self._write_text_atomic(
            self._path_for(project.project_id),
            project.model_dump_json(indent=2),
        )

    def get(self, project_id: UUID) -> Project:
        path = self._path_for(project_id)
        if not path.exists():
            raise ProjectNotFoundError(f"project not found: {project_id}")
        return Project.model_validate_json(path.read_text(encoding="utf-8"))


class JsonCaptureSessionRepository(_AtomicJsonRepository):
    """Local persistence for Chat 1 capture-session state."""

    def __init__(self, root: Path | str) -> None:
        super().__init__(root, "capture_sessions")

    def save(self, session: CaptureSession) -> None:
        self._write_text_atomic(
            self._path_for(session.session_id),
            session.model_dump_json(indent=2),
        )

    def get(self, session_id: UUID) -> CaptureSession:
        path = self._path_for(session_id)
        if not path.exists():
            raise CaptureSessionNotFoundError(f"capture session not found: {session_id}")
        return CaptureSession.model_validate_json(path.read_text(encoding="utf-8"))
