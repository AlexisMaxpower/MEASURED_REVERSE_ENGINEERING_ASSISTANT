from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

EXIT_OK = 0
EXIT_HOST_PREFLIGHT = 10
EXIT_INVALID_INPUT = 20
EXIT_CAD_TRANSFER = 40
EXIT_ARTIFACT = 50
EXIT_INTERNAL = 70


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the controlled MREA SOLIDWORKS 2026 real-host validation and emit runtime evidence."
    )
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--host-readiness", type=Path, required=True)
    parser.add_argument("--part-template", type=Path)
    parser.add_argument("--no-attach", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    return parser.parse_args()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _solidworks_revision_from_readiness(readiness: Any) -> str | None:
    for check in readiness.checks:
        if check.code != "SOLIDWORKS_VERSION_2026":
            continue
        details = dict(check.details or {})
        revision = details.get("revision_number")
        return str(revision) if revision else None
    return None


def _failure_evidence(*, build_runtime_evidence: Any, RuntimeDiagnostic: Any, readiness: Any,
                      sketch_package_id: str, solidworks_version: str | None,
                      code: str, stage: str, message: str) -> dict[str, Any]:
    return build_runtime_evidence(
        sketch_package_id=sketch_package_id,
        adapter_name="SOLIDWORKS_2026",
        real_host_executed=True,
        execution=None,
        host_readiness=readiness,
        solidworks_version=solidworks_version,
        diagnostics=(RuntimeDiagnostic(code=code, stage=stage, message=message),),
    )


def main() -> int:
    args = _parse_args()
    chat4_root = Path(__file__).resolve().parents[1]
    repo_root = chat4_root.parent
    sys.path.insert(0, str(chat4_root / "src"))

    try:
        from mrea_cad_bridge import (  # noqa: PLC0415
            CadAdapterError,
            CadRuntimeEvidenceError,
            RuntimeDiagnostic,
            SolidWorksAgentAdapter,
            SolidWorksAgentConfig,
            build_runtime_evidence,
            execute_cad_transfer_v1,
            parse_host_readiness_report,
            require_host_ready,
        )
    except Exception as exc:  # pragma: no cover - environment/bootstrap failure
        print(f"BOOTSTRAP_FAILED: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    fixture_path = repo_root / "tests" / "fixtures" / "contracts" / "sketch_package_v1.json"
    try:
        sketch_package = json.loads(fixture_path.read_text(encoding="utf-8"))
        readiness_payload = json.loads(args.host_readiness.read_text(encoding="utf-8"))
        readiness = parse_host_readiness_report(readiness_payload)
        require_host_ready(readiness)
    except (OSError, json.JSONDecodeError, CadRuntimeEvidenceError, KeyError, TypeError, ValueError) as exc:
        print(f"HOST_PREFLIGHT_FAILED: {exc}", file=sys.stderr)
        return EXIT_HOST_PREFLIGHT

    sketch_package_id = str(sketch_package.get("sketch_package_id") or "")
    if not sketch_package_id:
        print("INVALID_INPUT: sketch_package_id is missing", file=sys.stderr)
        return EXIT_INVALID_INPUT

    solidworks_version = _solidworks_revision_from_readiness(readiness)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runtime_evidence_path = args.output_dir / "runtime_evidence.json"

    config = SolidWorksAgentConfig(
        executable_path=args.agent,
        output_directory=args.output_dir,
        part_template_path=args.part_template,
        attach_to_running=not args.no_attach,
        allow_launch=not args.no_launch,
        timeout_seconds=300.0,
    )

    try:
        execution = execute_cad_transfer_v1(
            sketch_package=sketch_package,
            adapter=SolidWorksAgentAdapter(config),
            cad_package_id="CAD-SW-REALHOST-001",
            report_id="CADV-SW-REALHOST-001",
        )
    except CadAdapterError as exc:
        evidence = _failure_evidence(
            build_runtime_evidence=build_runtime_evidence,
            RuntimeDiagnostic=RuntimeDiagnostic,
            readiness=readiness,
            sketch_package_id=sketch_package_id,
            solidworks_version=solidworks_version,
            code="CAD_TRANSFER_FAILED",
            stage="CAD_TRANSFER",
            message=str(exc),
        )
        try:
            _write_json(runtime_evidence_path, evidence)
        except OSError as write_exc:
            print(f"ARTIFACT_FAILED: {write_exc}", file=sys.stderr)
            return EXIT_ARTIFACT
        print(f"CAD_TRANSFER_FAILED: {exc}", file=sys.stderr)
        return EXIT_CAD_TRANSFER
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        evidence = _failure_evidence(
            build_runtime_evidence=build_runtime_evidence,
            RuntimeDiagnostic=RuntimeDiagnostic,
            readiness=readiness,
            sketch_package_id=sketch_package_id,
            solidworks_version=solidworks_version,
            code="REAL_HOST_INTERNAL_FAILURE",
            stage="INTERNAL",
            message=str(exc),
        )
        try:
            _write_json(runtime_evidence_path, evidence)
        except OSError:
            pass
        print(f"INTERNAL_FAILURE: {exc}", file=sys.stderr)
        return EXIT_INTERNAL

    try:
        evidence = build_runtime_evidence(
            sketch_package_id=sketch_package_id,
            adapter_name="SOLIDWORKS_2026",
            real_host_executed=True,
            execution=execution,
            host_readiness=readiness,
            solidworks_version=solidworks_version,
        )
        cad_package_path = args.output_dir / "cad_package.json"
        verification_path = args.output_dir / "cad_verification.json"
        _write_json(cad_package_path, execution.cad_package)
        _write_json(verification_path, execution.cad_verification_report)
        _write_json(runtime_evidence_path, evidence)
    except CadRuntimeEvidenceError as exc:
        print(f"RUNTIME_EVIDENCE_FAILED [{exc.code}/{exc.stage}]: {exc}", file=sys.stderr)
        return EXIT_CAD_TRANSFER
    except OSError as exc:
        print(f"ARTIFACT_FAILED: {exc}", file=sys.stderr)
        return EXIT_ARTIFACT

    if evidence.get("status") != "VERIFIED":
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        print("REAL_HOST_RESULT=FAILED", file=sys.stderr)
        return EXIT_CAD_TRANSFER

    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print("REAL_HOST_RESULT=VERIFIED")
    print(f"RUNTIME_EVIDENCE={runtime_evidence_path}")
    print(f"CAD_PACKAGE={cad_package_path}")
    print(f"CAD_VERIFICATION={verification_path}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
