from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import url2pathname

QUALIFICATION_SCHEMA = "mrea.solidworks-host-qualification.v1"

HOST_BOUNDARY_FILES = (
    "chat_4_cad_bridge_verification/solidworks_agent/Mrea.SolidWorksCadAgent.csproj",
    "chat_4_cad_bridge_verification/solidworks_agent/Program.cs",
    "chat_4_cad_bridge_verification/solidworks_agent/ProtocolModels.cs",
    "chat_4_cad_bridge_verification/solidworks_agent/SolidWorksSession.cs",
    "chat_4_cad_bridge_verification/solidworks_agent/SolidWorksTransfer.cs",
    "chat_4_cad_bridge_verification/scripts/build_solidworks_agent.ps1",
    "chat_4_cad_bridge_verification/scripts/test_solidworks_host_readiness.ps1",
    "chat_4_cad_bridge_verification/scripts/run_solidworks_pass3_host_validation.ps1",
    "chat_4_cad_bridge_verification/scripts/run_solidworks_host_validation.py",
    "chat_4_cad_bridge_verification/scripts/finalize_solidworks_qualification.py",
    "chat_4_cad_bridge_verification/scripts/qualify_solidworks_host.ps1",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_agent.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_capabilities.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_constraint_handshake.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_dimension_capabilities.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_worker_handshake.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/solidworks_runtime_inputs.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/runtime_evidence.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/vendor.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/verification.py",
    "chat_4_cad_bridge_verification/src/mrea_cad_bridge/pipeline.py",
    "tests/fixtures/contracts/sketch_package_v1.json",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize one real SOLIDWORKS 2026 host qualification and close all three legacy host gates."
    )
    parser.add_argument("--runtime-inputs", type=Path, required=True)
    parser.add_argument("--prebuild-readiness", type=Path, required=True)
    parser.add_argument("--sketch-package", type=Path, required=True)
    parser.add_argument("--build-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", "LOCAL_WORKTREE"))
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def compute_host_boundary_fingerprint(repo_root: Path) -> tuple[str, list[dict[str, str]]]:
    entries: list[dict[str, str]] = []
    combined = hashlib.sha256()
    for relative in HOST_BOUNDARY_FILES:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"host-boundary file is missing: {relative}")
        digest = _sha256(path)
        entries.append({"path": relative, "sha256": digest})
        combined.update(relative.encode("utf-8"))
        combined.update(b"\0")
        combined.update(digest.encode("ascii"))
        combined.update(b"\0")
    return combined.hexdigest(), entries


def _required_check(payload: Mapping[str, Any], code: str) -> Mapping[str, Any]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("prebuild readiness checks are missing")
    matches = [item for item in checks if isinstance(item, Mapping) and item.get("code") == code]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one readiness check {code!r}")
    check = matches[0]
    if check.get("status") != "PASS":
        raise ValueError(f"readiness check {code!r} is not PASS: {check.get('status')!r}")
    return check


def _native_artifacts(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = evidence.get("artifacts")
    if not isinstance(raw, list):
        raise ValueError("runtime evidence artifacts are missing")
    native: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping) or item.get("kind") != "SOLIDWORKS_PART":
            continue
        uri = item.get("uri")
        digest = item.get("sha256")
        if not isinstance(uri, str) or not uri:
            raise ValueError("SOLIDWORKS_PART artifact URI is missing")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("SOLIDWORKS_PART artifact SHA-256 is invalid")
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise ValueError(f"SOLIDWORKS_PART artifact must be file://, got {uri!r}")
        local = Path(url2pathname(parsed.path))
        if not local.is_file():
            raise FileNotFoundError(f"native SOLIDWORKS artifact does not exist: {local}")
        if local.suffix.upper() != ".SLDPRT":
            raise ValueError(f"native artifact is not .SLDPRT: {local}")
        actual = _sha256(local)
        if actual.lower() != digest.lower():
            raise ValueError(f"native artifact SHA-256 mismatch: {local}")
        copied = dict(item)
        copied["validated_local_path"] = str(local)
        copied["validated_sha256"] = actual
        native.append(copied)
    if not native:
        raise ValueError("no validated SOLIDWORKS_PART artifact was produced")
    return native


def main() -> int:
    args = _parse_args()
    repo_root = _repo_root()
    chat4_src = repo_root / "chat_4_cad_bridge_verification" / "src"
    sys.path.insert(0, str(chat4_src))

    from mrea_cad_bridge import build_solidworks_runtime_evidence_from_inputs_v1  # noqa: PLC0415

    runtime_inputs = _load_json(args.runtime_inputs)
    prebuild = _load_json(args.prebuild_readiness)
    sketch_package = _load_json(args.sketch_package)

    _required_check(prebuild, "OS_WINDOWS_11_X64")
    _required_check(prebuild, "PROCESS_X64")
    _required_check(prebuild, "DOTNET_FRAMEWORK_48")
    _required_check(prebuild, "MSBUILD_AVAILABLE")
    _required_check(prebuild, "SOLIDWORKS_INTEROP_AVAILABLE")
    _required_check(prebuild, "SOLIDWORKS_COM_REGISTERED")
    _required_check(prebuild, "SOLIDWORKS_VERSION_2026")

    if not args.build_artifact.is_file():
        raise FileNotFoundError(f"production CAD Agent build artifact is missing: {args.build_artifact}")
    build_sha256 = _sha256(args.build_artifact)

    runtime_evidence = build_solidworks_runtime_evidence_from_inputs_v1(
        sketch_package=sketch_package,
        runtime_inputs=runtime_inputs,
    )
    if runtime_evidence.get("status") != "VERIFIED":
        raise RuntimeError(
            "real-host runtime evidence did not reach VERIFIED: "
            + str(runtime_evidence.get("status"))
        )
    if runtime_evidence.get("real_host_executed") is not True:
        raise RuntimeError("runtime evidence did not prove real_host_executed=true")
    if not runtime_evidence.get("solidworks_version"):
        raise RuntimeError("runtime evidence did not record SOLIDWORKS version")
    report = runtime_evidence.get("verification_report")
    if not isinstance(report, Mapping) or report.get("overall_status") != "VERIFIED":
        raise RuntimeError("canonical CAD read-back report is not VERIFIED")
    read_back = runtime_evidence.get("read_back_dimensions")
    if not isinstance(read_back, list) or not read_back:
        raise RuntimeError("runtime evidence contains no read-back dimensions")

    native = _native_artifacts(runtime_evidence)
    fingerprint, fingerprint_files = compute_host_boundary_fingerprint(repo_root)

    qualification = {
        "schema_version": QUALIFICATION_SCHEMA,
        "status": "VERIFIED",
        "source_commit": args.source_commit,
        "host_boundary_fingerprint": fingerprint,
        "gates": {
            "PRODUCTION_CSHARP_INTEROP_BUILD": "VERIFIED",
            "REAL_SOLIDWORKS_2026_HOST": "VERIFIED",
            "NATIVE_SLDPRT_GENERATION_READBACK": "VERIFIED",
        },
        "build": {
            "artifact": str(args.build_artifact.resolve()),
            "sha256": build_sha256,
            "official_interop_check": "PASS",
            "msbuild_check": "PASS",
        },
        "runtime_evidence": runtime_evidence,
        "validated_native_artifacts": native,
        "fingerprinted_files": fingerprint_files,
        "freshness_rule": (
            "Qualification remains reusable across later software rounds while the "
            "host_boundary_fingerprint is unchanged. Re-run only after a fingerprinted "
            "host-boundary file changes or the controlled host itself changes materially."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qualification, indent=2), encoding="utf-8")
    print("SOLIDWORKS_HOST_QUALIFICATION=VERIFIED")
    print(f"HOST_BOUNDARY_FINGERPRINT={fingerprint}")
    print(f"QUALIFICATION_MANIFEST={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
