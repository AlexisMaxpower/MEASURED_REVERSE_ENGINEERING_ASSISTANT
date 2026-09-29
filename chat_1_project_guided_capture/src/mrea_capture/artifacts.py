from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol

from .models import ArtifactRecord


class ArtifactNotFoundError(LookupError):
    pass


class ArtifactStore(Protocol):
    def put_bytes(self, data: bytes, *, media_type: str, extension: str) -> ArtifactRecord: ...

    def get_bytes(self, artifact: ArtifactRecord) -> bytes: ...


class FileSystemArtifactStore:
    """Content-addressed local artifact storage for offline capture.

    This is an internal Chat 1 adapter. `ArtifactRecord` is not the shared
    `ArtifactReference` contract owned by Integrator.
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._artifacts_dir = self._root / "artifacts"
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_extension(extension: str) -> str:
        value = extension.strip().lower()
        if not value:
            raise ValueError("artifact extension cannot be blank")
        if not value.startswith("."):
            value = f".{value}"
        if any(character not in ".abcdefghijklmnopqrstuvwxyz0123456789" for character in value):
            raise ValueError("artifact extension contains unsupported characters")
        return value

    def put_bytes(self, data: bytes, *, media_type: str, extension: str) -> ArtifactRecord:
        if not data:
            raise ValueError("artifact data cannot be empty")
        if not media_type.strip():
            raise ValueError("media_type cannot be blank")

        suffix = self._normalize_extension(extension)
        digest = hashlib.sha256(data).hexdigest()
        relative = Path(digest[:2]) / f"{digest}{suffix}"
        target = self._artifacts_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if not target.exists():
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(data)
            os.replace(temporary, target)

        return ArtifactRecord(
            relative_path=str(relative.as_posix()),
            media_type=media_type.strip(),
            size_bytes=len(data),
            sha256=digest,
        )

    def get_bytes(self, artifact: ArtifactRecord) -> bytes:
        path = self._artifacts_dir / artifact.relative_path
        if not path.exists():
            raise ArtifactNotFoundError(f"artifact not found: {artifact.artifact_id}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != artifact.sha256:
            raise ValueError(f"artifact checksum mismatch: {artifact.artifact_id}")
        return data
