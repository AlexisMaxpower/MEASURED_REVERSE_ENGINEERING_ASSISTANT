from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import url2pathname

HOST_READINESS_SCHEMA = "mrea.cad-host-readiness.v1"
RUNTIME_INPUTS_SCHEMA = "mrea.solidworks-runtime-inputs.v1"
ADAPTER_NAME = "SOLIDWORKS_2026"
REQUIRED_READINESS_CODES = frozenset(
    {
        "OS_WINDOWS_11_X64",
        "PROCESS_X64",
        "DOTNET_FRAMEWORK_48",
        "AGENT_EXECUTABLE_AVAILABLE",
        "SOLIDWORKS_COM_REGISTERED",
        "SOLIDWORKS_VERSION_2026",
        "SOLIDWORKS_INTEROP_AVAILABLE",
        "OUTPUT_PATH_WRITABLE",
        "PART_TEMPLATE_AVAILABLE",
    }
)

EXIT_OK = 0
EXIT_HOST_NOT_READY = 10
EXIT_INVALID_INPUT = 20
EXIT_SOLIDWORKS_STARTUP = 30
EXIT_CAD_TRANSFER = 40
EXIT_ARTIFACT = 50
EXIT_UNEXPECTED = 70
KNOWN_AGENT_EXITS = {
    EXIT_OK,
    EXIT_INVALID_INPUT,
    EXIT_SOLIDWORKS_STARTUP,
    EXIT_CAD_TRANSFER,
    EXIT_ARTIFACT,
    EXIT_UNEXPECTED,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Side Chat 4B SOLIDWORKS real-host producer. "
            "This emits host/runtime evidence inputs but does not decide final runtime VERIFIED."
        )
    )
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--host-readiness", type=Path, required=True)
    parser.add_argument("--part-template", type=Path)
    parser.add_argument("--no-attach", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def recompute_host_readiness(payload: Mapping[str, Any]) -> str:
    if payload.get("schema_version") != HOST_READINESS_SCHEMA:
        raise ValueError("host-readiness schema mismatch")
    if payload.get("adapter_name") != ADAPTER_NAME:
        raise ValueError("host-readiness adapter mismatch")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("host-readiness checks must be an array")

    required_statuses: list[str] = []
    seen_codes: set[str] = set()
    for item in checks:
        if not isinstance(item, Mapping):
            raise ValueError("host-readiness check must be an object")
        code = item.get("code")
        if not isinstance(code, str) or not code:
            raise ValueError("host-readiness check code must be a non-empty string")
        if code in seen_codes:
            raise ValueError(f"duplicate host-readiness check code: {code}")
        seen_codes.add(code)
        if item.get("required", True):
            status = item.get("status")
            if status not in {"PASS", "FAIL", "UNVERIFIED"}:
                raise ValueError("host-readiness check has invalid status")
            required_statuses.append(str(status))

    missing = sorted(REQUIRED_READINESS_CODES - seen_codes)
    if missing:
        raise ValueError(f"host-readiness report is missing required checks: {missing!r}")

    if "FAIL" in required_statuses:
        computed = "FAILED"
    elif "UNVERIFIED" in required_statuses:
        computed = "UNVERIFIED"
    else:
        computed = "READY"

    reported = payload.get("status")
    if reported is not None and reported != computed:
        raise ValueError(
            f"host-readiness reported status {reported!r} disagrees with computed {computed!r}"
        )
    return computed


def _diagnostic(
    code: str,
    stage: str,
    message: str,
    *,
    severity: str = "ERROR",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "code": code,
        "stage": stage,
        "message": message,
        "severity": severity,
    }
    if details:
        item["details"] = dict(details)
    return item


def _invoke_agent(
    *,
    agent: Path,
    request: Mapping[str, Any],
    timeout_seconds: float,
) -> tuple[int, dict[str, Any] | None, str, str]:
    with tempfile.TemporaryDirectory(prefix="mrea-sw-pass3-") as temp_dir:
        temp_root = Path(temp_dir)
        request_path = temp_root / "request.json"
        response_path = temp_root / "response.json"
        _write_json(request_path, request)

        try:
            completed = subprocess.run(
                [
                    str(agent),
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                ],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return (
                EXIT_CAD_TRANSFER,
                None,
                exc.stdout or "",
                exc.stderr or f"agent timed out after {timeout_seconds:g} seconds",
            )

        response: dict[str, Any] | None = None
        if response_path.is_file():
            try:
                response = _load_json(response_path)
            except (OSError, json.JSONDecodeError, ValueError):
                response = None
        return completed.returncode, response, completed.stdout, completed.stderr


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_native_artifacts(artifacts: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    native = [item for item in artifacts if item.get("kind") == "SOLIDWORKS_PART"]
    if not native:
        return [
            _diagnostic(
                "NATIVE_ARTIFACT_MISSING",
                "ARTIFACT",
                "agent response did not include a SOLIDWORKS_PART artifact",
            )
        ]

    for artifact in native:
        uri = artifact.get("uri")
        expected = artifact.get("sha256")
        if not isinstance(uri, str) or not uri:
            diagnostics.append(
                _diagnostic("ARTIFACT_URI_MISSING", "ARTIFACT", "native artifact URI is missing")
            )
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            diagnostics.append(
                _diagnostic("ARTIFACT_SHA256_INVALID", "ARTIFACT", "native artifact SHA-256 is missing or invalid")
            )
            continue

        parsed = urlparse(uri)
        if parsed.scheme != "file":
            diagnostics.append(
                _diagnostic(
                    "ARTIFACT_URI_UNSUPPORTED",
                    "ARTIFACT",
                    "native artifact URI must use file:// for controlled host verification",
                    details={"uri": uri},
                )
            )
            continue

        path = Path(url2pathname(parsed.path))
        if not path.is_file():
            diagnostics.append(
                _diagnostic(
                    "ARTIFACT_FILE_MISSING",
                    "ARTIFACT",
                    "native artifact path from agent response does not exist",
                    details={"path": str(path)},
                )
            )
            continue

        actual = _sha256(path)
        if actual.lower() != expected.lower():
            diagnostics.append(
                _diagnostic(
                    "ARTIFACT_SHA256_MISMATCH",
                    "ARTIFACT",
                    "native artifact SHA-256 does not match the agent response",
                    details={"expected": expected, "actual": actual, "path": str(path)},
                )
            )
    return diagnostics


def build_runtime_inputs(
    *,
    host_readiness: Mapping[str, Any],
    request: Mapping[str, Any],
    agent_exit_code: int,
    agent_response: Mapping[str, Any] | None,
    canonical_verification_report: Mapping[str, Any] | None,
    extra_diagnostics: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    response = dict(agent_response or {})
    read_back = response.get("read_back")
    if not isinstance(read_back, Mapping):
        read_back = {}
    diagnostics = [dict(item) for item in response.get("diagnostics", ()) if isinstance(item, Mapping)]
    diagnostics.extend(dict(item) for item in (extra_diagnostics or ()))

    return {
        "schema_version": RUNTIME_INPUTS_SCHEMA,
        "producer": "SIDE_CHAT_4B",
        "adapter_name": response.get("adapter_name", request.get("adapter_name")),
        "host_readiness": dict(host_readiness),
        "agent_exit_code": agent_exit_code,
        "real_host_executed": bool(response.get("real_host_executed", False)),
        "solidworks_version": response.get("solidworks_version"),
        "sketch_package_id": request.get("sketch_package_id"),
        "bindings": [dict(item) for item in response.get("bindings", ()) if isinstance(item, Mapping)],
        "read_back_dimensions": [
            dict(item) for item in read_back.get("dimensions", ()) if isinstance(item, Mapping)
        ],
        "constraint_conflicts": list(read_back.get("constraint_conflicts", ())),
        "artifacts": [dict(item) for item in response.get("artifacts", ()) if isinstance(item, Mapping)],
        "diagnostics": diagnostics,
        "canonical_verification_report": (
            dict(canonical_verification_report)
            if canonical_verification_report is not None
            else None
        ),
    }


class _RecordedAdapter:
    adapter_name = ADAPTER_NAME

    def __init__(self, result: Any) -> None:
        self._result = result

    def transfer(self, package: Any) -> Any:
        return self._result


def _write_failure_bundle(
    *,
    path: Path,
    readiness: Mapping[str, Any],
    request: Mapping[str, Any],
    process_exit: int,
    response: Mapping[str, Any] | None,
    diagnostics: list[Mapping[str, Any]],
) -> None:
    _write_json(
        path,
        build_runtime_inputs(
            host_readiness=readiness,
            request=request,
            agent_exit_code=process_exit,
            agent_response=response,
            canonical_verification_report=None,
            extra_diagnostics=diagnostics,
        ),
    )


def main() -> int:
    args = _parse_args()
    if args.timeout_seconds <= 0:
        print("timeout must be > 0", file=sys.stderr)
        return EXIT_INVALID_INPUT

    args.output_dir.mkdir(parents=True, exist_ok=True)
    inputs_path = args.output_dir / "solidworks_runtime_inputs.json"
    raw_response_path = args.output_dir / "solidworks_agent_response.json"

    try:
        readiness = _load_json(args.host_readiness)
        readiness_status = recompute_host_readiness(readiness)
    except Exception as exc:
        print(f"HOST_READINESS_INVALID: {exc}", file=sys.stderr)
        return EXIT_HOST_NOT_READY

    if readiness_status != "READY":
        print(f"HOST_READINESS_NOT_READY: {readiness_status}", file=sys.stderr)
        return EXIT_HOST_NOT_READY

    chat4_root = Path(__file__).resolve().parents[1]
    repo_root = chat4_root.parent
    sys.path.insert(0, str(chat4_root / "src"))

    try:
        from mrea_cad_bridge import (  # noqa: PLC0415
            SolidWorksAgentConfig,
            build_solidworks_agent_request,
            execute_cad_transfer_v1,
            map_sketch_package_v1,
            parse_solidworks_agent_response,
        )

        fixture_path = repo_root / "tests" / "fixtures" / "contracts" / "sketch_package_v1.json"
        sketch_package = _load_json(fixture_path)
        mapped = map_sketch_package_v1(sketch_package)
        config = SolidWorksAgentConfig(
            executable_path=args.agent,
            output_directory=args.output_dir,
            part_template_path=args.part_template,
            attach_to_running=not args.no_attach,
            allow_launch=not args.no_launch,
            timeout_seconds=args.timeout_seconds,
        )
        request = build_solidworks_agent_request(mapped, config)
    except Exception as exc:
        print(f"REQUEST_BUILD_FAILED: {exc}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    process_exit, response, stdout, stderr = _invoke_agent(
        agent=args.agent,
        request=request,
        timeout_seconds=args.timeout_seconds,
    )

    if response is not None:
        _write_json(raw_response_path, response)

    process_diagnostics: list[dict[str, Any]] = []
    if response is None:
        process_diagnostics.append(
            _diagnostic(
                "AGENT_RESPONSE_MISSING",
                "AGENT_STARTUP",
                "CAD Agent did not produce a readable response JSON",
                details={"stdout": stdout.strip(), "stderr": stderr.strip(), "exit_code": process_exit},
            )
        )
        _write_failure_bundle(
            path=inputs_path,
            readiness=readiness,
            request=request,
            process_exit=process_exit,
            response=None,
            diagnostics=process_diagnostics,
        )
        return process_exit if process_exit in KNOWN_AGENT_EXITS and process_exit != 0 else EXIT_UNEXPECTED

    response_exit = response.get("exit_code")
    if not isinstance(response_exit, int) or response_exit != process_exit:
        process_diagnostics.append(
            _diagnostic(
                "AGENT_EXIT_CODE_MISMATCH",
                "AGENT_STARTUP",
                "process exit code disagrees with response exit_code",
                details={"process_exit": process_exit, "response_exit": response_exit},
            )
        )
        _write_failure_bundle(
            path=inputs_path,
            readiness=readiness,
            request=request,
            process_exit=process_exit,
            response=response,
            diagnostics=process_diagnostics,
        )
        return EXIT_UNEXPECTED

    if process_exit != EXIT_OK or response.get("status") != "OK":
        _write_failure_bundle(
            path=inputs_path,
            readiness=readiness,
            request=request,
            process_exit=process_exit,
            response=response,
            diagnostics=process_diagnostics,
        )
        return process_exit if process_exit in KNOWN_AGENT_EXITS and process_exit != 0 else EXIT_UNEXPECTED

    if response.get("real_host_executed") is not True:
        process_diagnostics.append(
            _diagnostic(
                "REAL_HOST_EXECUTION_FLAG_MISSING",
                "SOLIDWORKS_COM",
                "successful CAD Agent response did not assert real_host_executed=true",
            )
        )
    if not isinstance(response.get("solidworks_version"), str) or not response.get("solidworks_version"):
        process_diagnostics.append(
            _diagnostic(
                "SOLIDWORKS_VERSION_MISSING",
                "SOLIDWORKS_COM",
                "successful CAD Agent response did not record the actual SOLIDWORKS version",
            )
        )
    if process_diagnostics:
        _write_failure_bundle(
            path=inputs_path,
            readiness=readiness,
            request=request,
            process_exit=process_exit,
            response=response,
            diagnostics=process_diagnostics,
        )
        return EXIT_ARTIFACT

    try:
        adapter_result = parse_solidworks_agent_response(response)
        execution = execute_cad_transfer_v1(
            sketch_package=sketch_package,
            adapter=_RecordedAdapter(adapter_result),
            cad_package_id="CAD-SW-PASS3-HOST-001",
            report_id="CADV-SW-PASS3-HOST-001",
        )
    except Exception as exc:
        process_diagnostics.append(
            _diagnostic(
                "CANONICAL_VERIFICATION_FAILED",
                "READ_BACK",
                str(exc),
            )
        )
        _write_failure_bundle(
            path=inputs_path,
            readiness=readiness,
            request=request,
            process_exit=process_exit,
            response=response,
            diagnostics=process_diagnostics,
        )
        return EXIT_CAD_TRANSFER

    cad_package_path = args.output_dir / "cad_package.json"
    verification_path = args.output_dir / "cad_verification.json"
    _write_json(cad_package_path, execution.cad_package)
    _write_json(verification_path, execution.cad_verification_report)

    artifact_diagnostics = verify_native_artifacts(
        [item for item in response.get("artifacts", ()) if isinstance(item, Mapping)]
    )
    process_diagnostics.extend(artifact_diagnostics)

    bundle = build_runtime_inputs(
        host_readiness=readiness,
        request=request,
        agent_exit_code=process_exit,
        agent_response=response,
        canonical_verification_report=execution.cad_verification_report,
        extra_diagnostics=process_diagnostics,
    )
    _write_json(inputs_path, bundle)

    if artifact_diagnostics:
        print(f"ARTIFACT_EVIDENCE_FAILED: see {inputs_path}", file=sys.stderr)
        return EXIT_ARTIFACT

    if execution.cad_verification_report.get("overall_status") != "VERIFIED":
        print(f"CANONICAL_CAD_VERIFICATION=FAILED; see {verification_path}", file=sys.stderr)
        return EXIT_CAD_TRANSFER

    print("CANONICAL_CAD_VERIFICATION=VERIFIED")
    print("FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4")
    print(f"HOST_READINESS={args.host_readiness}")
    print(f"AGENT_RESPONSE={raw_response_path}")
    print(f"RUNTIME_EVIDENCE_INPUTS={inputs_path}")
    print(f"CAD_PACKAGE={cad_package_path}")
    print(f"CAD_VERIFICATION={verification_path}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
