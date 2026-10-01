from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

CURRENT_CONTROL_PATHS = (
    "chat_6_orchestrator/ORCHESTRATION_STATE.md",
    "chat_6_orchestrator/SLICE_STATUS.md",
    "chat_1_project_guided_capture/ORCHESTRATOR_DIRECTIVE.md",
    "chat_2_physical_measurement/ORCHESTRATOR_DIRECTIVE.md",
    "chat_3_geometry_semi_automatic_sketch/ORCHESTRATOR_DIRECTIVE.md",
    "chat_4_cad_bridge_verification/ORCHESTRATOR_DIRECTIVE.md",
    "chat_5_lifecycle_engineering_knowledge/ORCHESTRATOR_DIRECTIVE.md",
)

LEGACY_ROUND_ASSIGNMENTS = (
    "REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED",
    "PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED",
    "NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_legacy_solidworks_external_flags_cannot_return_to_current_round_authority() -> None:
    for relative in CURRENT_CONTROL_PATHS:
        text = _read(relative)
        for legacy in LEGACY_ROUND_ASSIGNMENTS:
            assert legacy not in text, f"legacy per-round SOLIDWORKS gate returned in {relative}: {legacy}"


def test_standing_qualification_is_explicitly_out_of_band() -> None:
    state = _read("chat_6_orchestrator/ORCHESTRATION_STATE.md")
    assert "SOLIDWORKS_HOST_QUALIFICATION = NOT_YET_EXECUTED_ON_REGISTERED_HOST" in state
    assert "ROUND_LEVEL_SOFTWARE_BLOCKER = FALSE" in state
    assert "LEGACY_THREE_LINE_CARRY_FORWARD = RETIRED" in state


def test_dedicated_real_host_workflow_is_self_hosted_and_manual() -> None:
    workflow = _read(".github/workflows/solidworks_host_qualification.yml")
    assert "workflow_dispatch:" in workflow
    assert "runs-on: [self-hosted, Windows, X64, solidworks-2026]" in workflow
    assert "qualify_solidworks_host.ps1" in workflow
    assert "PRODUCTION_CSHARP_INTEROP_BUILD" in workflow
    assert "REAL_SOLIDWORKS_2026_HOST" in workflow
    assert "NATIVE_SLDPRT_GENERATION_READBACK" in workflow


def test_qualification_finalizer_is_python_syntax_valid() -> None:
    relative = "chat_4_cad_bridge_verification/scripts/finalize_solidworks_qualification.py"
    source = _read(relative)
    compile(source, relative, "exec")


def test_one_shot_host_script_freshly_builds_runs_host_and_finalizes() -> None:
    script = _read("chat_4_cad_bridge_verification/scripts/qualify_solidworks_host.ps1")
    required_fragments = (
        "build_solidworks_agent.ps1",
        "run_solidworks_pass3_host_validation.ps1",
        "finalize_solidworks_qualification.py",
        "SOLIDWORKS_HOST_QUALIFICATION=VERIFIED",
    )
    for fragment in required_fragments:
        assert fragment in script
