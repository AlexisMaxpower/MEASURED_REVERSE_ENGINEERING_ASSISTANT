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

CURRENT_STATUS_GLOBS = (
    "chat_*/README.md",
    "chat_*/docs/IMPLEMENTATION_STATE.md",
)

LEGACY_ROUND_ASSIGNMENTS = (
    "REAL_SOLIDWORKS_2026_HOST = EXTERNAL_GATE_UNVERIFIED",
    "PRODUCTION_CSHARP_INTEROP_BUILD = UNVERIFIED",
    "NATIVE_SLDPRT_GENERATION_READBACK = UNVERIFIED",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _current_status_paths() -> tuple[Path, ...]:
    paths = {REPO_ROOT / relative for relative in CURRENT_CONTROL_PATHS}
    for pattern in CURRENT_STATUS_GLOBS:
        paths.update(path for path in REPO_ROOT.glob(pattern) if path.is_file())
    return tuple(sorted(paths))


def test_legacy_solidworks_external_flags_cannot_return_to_current_round_authority() -> None:
    for path in _current_status_paths():
        text = path.read_text(encoding="utf-8")
        for legacy in LEGACY_ROUND_ASSIGNMENTS:
            assert legacy not in text, (
                "legacy per-round SOLIDWORKS gate returned in current status surface "
                f"{path.relative_to(REPO_ROOT)}: {legacy}"
            )


def test_standing_qualification_uses_dynamic_workflow_authority() -> None:
    state = _read("chat_6_orchestrator/ORCHESTRATION_STATE.md")
    assert "SOLIDWORKS_HOST_QUALIFICATION = DEDICATED_WORKFLOW_AUTHORITY" in state
    assert "QUALIFICATION_WORKFLOW = .github/workflows/solidworks_host_qualification.yml" in state
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


def test_host_boundary_fingerprint_covers_dimension_shape_capability_contract() -> None:
    finalizer = _read("chat_4_cad_bridge_verification/scripts/finalize_solidworks_qualification.py")
    assert (
        '"chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_dimension_capabilities.py"'
        in finalizer
    )
    assert (
        '"chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_worker_handshake.py"'
        in finalizer
    )


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
