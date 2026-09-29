from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from mrea_capture.models import PartContext, ProjectStatus
from mrea_capture.repositories import JsonProjectRepository, ProjectNotFoundError
from mrea_capture.services import ProjectService


def build_part() -> PartContext:
    return PartContext(
        part_type="внутренняя дверца морозильной камеры",
        equipment="холодильник XXX",
        problem="сломана левая петля",
        reverse_engineering_reason="replacement part",
        target_manufacturing_method="FDM prototype",
    )


def test_project_is_created_and_restored_from_disk(tmp_path: Path) -> None:
    repository = JsonProjectRepository(tmp_path)
    service = ProjectService(repository)

    created = service.create_project(name="FREEZER_DOOR_001", part=build_part())
    restored = service.get_project(created.project_id)

    assert restored == created
    assert restored.status is ProjectStatus.ACTIVE
    assert (tmp_path / "projects" / f"{created.project_id}.json").exists()


def test_unknown_project_raises_explicit_error(tmp_path: Path) -> None:
    service = ProjectService(JsonProjectRepository(tmp_path))

    with pytest.raises(ProjectNotFoundError):
        service.get_project(uuid4())


def test_project_rejects_blank_name(tmp_path: Path) -> None:
    service = ProjectService(JsonProjectRepository(tmp_path))

    with pytest.raises(ValidationError):
        service.create_project(name="   ", part=build_part())
