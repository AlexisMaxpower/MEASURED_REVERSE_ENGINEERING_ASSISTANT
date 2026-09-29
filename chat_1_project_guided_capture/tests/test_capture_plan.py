from mrea_capture.models import CaptureViewStatus, CaptureViewType, PartContext, Project
from mrea_capture.services import CapturePlanService


def build_project() -> Project:
    return Project(name="P001", part=PartContext(part_type="flat bracket"))


def test_default_plan_contains_only_front_baseline() -> None:
    plan = CapturePlanService().create_plan(build_project())

    assert [item.view for item in plan.items] == [CaptureViewType.FRONT]
    assert plan.items[0].sequence == 1
    assert plan.items[0].required is True


def test_explicit_plan_preserves_order_and_removes_duplicates() -> None:
    project = build_project()
    plan = CapturePlanService().create_plan(
        project,
        views=[
            CaptureViewType.FRONT,
            CaptureViewType.TOP,
            CaptureViewType.FRONT,
            CaptureViewType.OPTIONAL_3Q,
        ],
    )

    assert [item.view for item in plan.items] == [
        CaptureViewType.FRONT,
        CaptureViewType.TOP,
        CaptureViewType.OPTIONAL_3Q,
    ]
    assert [item.sequence for item in plan.items] == [1, 2, 3]
    assert plan.items[-1].required is False


def test_session_is_initialized_from_plan_without_capture_side_effects() -> None:
    project = build_project()
    service = CapturePlanService()
    plan = service.create_plan(project, views=[CaptureViewType.FRONT, CaptureViewType.TOP])

    session = service.start_session(plan)

    assert session.project_id == project.project_id
    assert session.plan_id == plan.plan_id
    assert [view.status for view in session.views] == [
        CaptureViewStatus.PLANNED,
        CaptureViewStatus.PLANNED,
    ]
