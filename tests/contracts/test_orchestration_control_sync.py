from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / "chat_6_orchestrator/ORCHESTRATION_STATE.md"
DIRECTIVE_PATHS = (
    REPO_ROOT / "chat_1_project_guided_capture/ORCHESTRATOR_DIRECTIVE.md",
    REPO_ROOT / "chat_2_physical_measurement/ORCHESTRATOR_DIRECTIVE.md",
    REPO_ROOT / "chat_3_geometry_semi_automatic_sketch/ORCHESTRATOR_DIRECTIVE.md",
    REPO_ROOT / "chat_4_cad_bridge_verification/ORCHESTRATOR_DIRECTIVE.md",
    REPO_ROOT / "chat_5_lifecycle_engineering_knowledge/ORCHESTRATOR_DIRECTIVE.md",
)


def _state_authority() -> tuple[str, str]:
    state = STATE_PATH.read_text(encoding="utf-8")
    revision_match = re.search(r"^\*\*Directive revision:\*\* `([^`]+)`", state, re.MULTILINE)
    closed_rounds = re.findall(r"^ROUND_(\d+)_CLOSED = TRUE$", state, re.MULTILINE)

    assert revision_match is not None, "central orchestration state must declare directive revision"
    assert len(closed_rounds) == 1, (
        "central orchestration state must expose exactly one active ROUND_N_CLOSED authority; "
        f"found {closed_rounds}"
    )
    assert "NEXT_FULL_WORKER_PASS = READY" in state
    return revision_match.group(1), closed_rounds[0]


def test_worker_directives_match_current_closed_round_and_revision() -> None:
    revision, round_number = _state_authority()
    required_round_line = f"ROUND_{round_number}_CLOSED = TRUE"

    for path in DIRECTIVE_PATHS:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(REPO_ROOT)
        assert f"**Revision:** `{revision}`" in text, (
            f"{relative} does not match central directive revision {revision}"
        )
        assert required_round_line in text, (
            f"{relative} does not point to current closed round {round_number}"
        )
        assert "NEXT_FULL_WORKER_PASS = READY" in text, (
            f"{relative} does not require next-worker readiness"
        )
        assert "**Status:** `READY_FOR_NEXT_FULL_WORKER_PASS_FROM_CURRENT_MAIN`" in text
        assert "then-current shared `main`" in text


def test_closed_round_status_and_slice_status_are_synchronized() -> None:
    revision, round_number = _state_authority()
    state = STATE_PATH.read_text(encoding="utf-8")
    slice_status = (REPO_ROOT / "chat_6_orchestrator/SLICE_STATUS.md").read_text(encoding="utf-8")

    expected_status = f"ROUND_{round_number}_CLOSED_GREEN_SOFTWARE"
    assert f"**Status:** `{expected_status}`" in state
    assert f"**Central round:** {round_number}" in slice_status
    assert f"**Directive:** `{revision}`" in slice_status
    assert f"**Status:** `{expected_status}`" in slice_status
    assert f"ROUND_{round_number}_CLOSED = TRUE" in slice_status
    assert "NEXT_FULL_WORKER_PASS = READY" in slice_status
