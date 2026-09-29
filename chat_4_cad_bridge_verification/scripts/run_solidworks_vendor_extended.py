from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


PROTOCOL = "mrea.solidworks-agent.v1"
ADAPTER = "SOLIDWORKS_2026"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Chat 4B vendor-only SOLIDWORKS 2026 extended smoke test."
    )
    parser.add_argument("--agent", type=Path, required=True, help="Path to Mrea.SolidWorksCadAgent.exe")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for generated .SLDPRT artifact")
    parser.add_argument("--part-template", type=Path, help="Optional explicit SOLIDWORKS .prtdot template")
    parser.add_argument("--no-attach", action="store_true", help="Do not attach to an already running SOLIDWORKS")
    parser.add_argument("--no-launch", action="store_true", help="Do not launch SOLIDWORKS if attach fails")
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _request(args: argparse.Namespace) -> dict:
    return {
        "protocol_version": PROTOCOL,
        "adapter_name": ADAPTER,
        "sketch_package_id": "SW-VENDOR-EXTENDED-001",
        "output_directory": str(args.output_dir.resolve()),
        "part_template_path": (
            str(args.part_template.resolve()) if args.part_template is not None else None
        ),
        "attach_to_running": not args.no_attach,
        "allow_launch": not args.no_launch,
        "entities": [
            {"entity_id": "P-ON-LINE", "type": "POINT", "point": {"x": 20.0, "y": 0.0}},
            {
                "entity_id": "L-HORIZONTAL",
                "type": "LINE",
                "start": {"x": 0.0, "y": 0.0},
                "end": {"x": 40.0, "y": 0.0},
            },
            {
                "entity_id": "L-VERTICAL",
                "type": "LINE",
                "start": {"x": 50.0, "y": 0.0},
                "end": {"x": 50.0, "y": 30.0},
            },
            {
                "entity_id": "C-OUTER",
                "type": "CIRCLE",
                "center": {"x": 10.0, "y": 20.0},
                "radius": 5.0,
            },
            {
                "entity_id": "C-INNER",
                "type": "CIRCLE",
                "center": {"x": 10.0, "y": 20.0},
                "radius": 3.0,
            },
            {
                "entity_id": "C-EQUAL",
                "type": "CIRCLE",
                "center": {"x": 30.0, "y": 20.0},
                "radius": 5.0,
            },
            {
                "entity_id": "A-CCW",
                "type": "ARC",
                "center": {"x": 65.0, "y": 20.0},
                "radius": 5.0,
                "start_angle_deg": 0.0,
                "end_angle_deg": 120.0,
            },
        ],
        "constraints": [
            {
                "constraint_id": "K-H",
                "type": "HORIZONTAL",
                "entity_ids": ["L-HORIZONTAL"],
                "status": "VERIFIED",
            },
            {
                "constraint_id": "K-V",
                "type": "VERTICAL",
                "entity_ids": ["L-VERTICAL"],
                "status": "VERIFIED",
            },
            {
                "constraint_id": "K-CONC",
                "type": "CONCENTRIC",
                "entity_ids": ["C-OUTER", "C-INNER"],
                "status": "VERIFIED",
            },
            {
                "constraint_id": "K-EQUAL",
                "type": "EQUAL",
                "entity_ids": ["C-OUTER", "C-EQUAL"],
                "status": "VERIFIED",
            },
            {
                "constraint_id": "K-COINC",
                "type": "COINCIDENT",
                "entity_ids": ["P-ON-LINE", "L-HORIZONTAL"],
                "status": "VERIFIED",
            },
        ],
        "dimensions": [
            {
                "dimension_id": "D-LENGTH",
                "measurement_id": "M-LENGTH",
                "type": "DISTANCE",
                "value": 40.0,
                "unit": "mm",
                "entity_ids": ["L-HORIZONTAL"],
            },
            {
                "dimension_id": "D-DIAMETER",
                "measurement_id": "M-DIAMETER",
                "type": "DIAMETER",
                "value": 10.0,
                "unit": "mm",
                "entity_ids": ["C-OUTER"],
            },
            {
                "dimension_id": "D-RADIUS",
                "measurement_id": "M-RADIUS",
                "type": "RADIUS",
                "value": 5.0,
                "unit": "mm",
                "entity_ids": ["A-CCW"],
            },
            {
                "dimension_id": "D-CENTER",
                "measurement_id": "M-CENTER",
                "type": "DISTANCE",
                "value": 20.0,
                "unit": "mm",
                "entity_ids": ["C-OUTER", "C-EQUAL"],
            },
        ],
    }


def main() -> int:
    args = _parse_args()
    if not args.agent.is_file():
        raise SystemExit(f"Agent executable not found: {args.agent}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    request = _request(args)
    with tempfile.TemporaryDirectory(prefix="mrea-sw-4b-") as temp:
        temp_root = Path(temp)
        request_path = temp_root / "request.json"
        response_path = temp_root / "response.json"
        request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")

        completed = subprocess.run(
            [
                str(args.agent),
                "--request",
                str(request_path),
                "--response",
                str(response_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if not response_path.is_file():
            print(completed.stdout)
            print(completed.stderr)
            print("VENDOR_EXTENDED_RESULT=FAILED")
            return 2

        response = json.loads(response_path.read_text(encoding="utf-8"))

    print(json.dumps(response, indent=2))
    if completed.returncode != 0 or response.get("status") != "OK":
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2
    if response.get("protocol_version") != PROTOCOL or response.get("adapter_name") != ADAPTER:
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2

    expected = {
        "D-LENGTH": 40.0,
        "D-DIAMETER": 10.0,
        "D-RADIUS": 5.0,
        "D-CENTER": 20.0,
    }
    actual = {
        item["dimension_id"]: float(item["actual_value"])
        for item in response.get("read_back", {}).get("dimensions", [])
    }
    if set(actual) != set(expected):
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2
    if any(abs(actual[key] - value) > 1e-6 for key, value in expected.items()):
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2

    conflicts = response.get("read_back", {}).get("constraint_conflicts", [])
    if conflicts:
        print(f"Unexpected constraint conflicts: {conflicts}")
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2

    artifact = args.output_dir.resolve() / "SW-VENDOR-EXTENDED-001.SLDPRT"
    if not artifact.is_file():
        print(f"Native artifact missing: {artifact}")
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2

    artifacts = response.get("artifacts", [])
    if len(artifacts) != 1 or artifacts[0].get("sha256") != _sha256(artifact):
        print("Artifact metadata/hash mismatch.")
        print("VENDOR_EXTENDED_RESULT=FAILED")
        return 2

    print("VENDOR_EXTENDED_RESULT=VERIFIED")
    print(f"NATIVE_ARTIFACT={artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
