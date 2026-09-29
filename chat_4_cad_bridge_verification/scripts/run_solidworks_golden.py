from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MREA Chat 4 SOLIDWORKS numerical golden transfer. "
            "This does not decide final real-host runtime verification."
        )
    )
    parser.add_argument("--agent", type=Path, required=True, help="Path to Mrea.SolidWorksCadAgent.exe")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for generated SLDPRT/report artifacts")
    parser.add_argument("--part-template", type=Path, help="Optional explicit SOLIDWORKS .prtdot template")
    parser.add_argument("--no-attach", action="store_true", help="Do not attach to an already running SOLIDWORKS")
    parser.add_argument("--no-launch", action="store_true", help="Do not launch SOLIDWORKS if attach fails")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    chat4_root = Path(__file__).resolve().parents[1]
    repo_root = chat4_root.parent
    sys.path.insert(0, str(chat4_root / "src"))

    from mrea_cad_bridge import (  # noqa: PLC0415
        SolidWorksAgentAdapter,
        SolidWorksAgentConfig,
        execute_cad_transfer_v1,
    )

    fixture_path = repo_root / "tests" / "fixtures" / "contracts" / "sketch_package_v1.json"
    sketch_package = json.loads(fixture_path.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = SolidWorksAgentConfig(
        executable_path=args.agent,
        output_directory=args.output_dir,
        part_template_path=args.part_template,
        attach_to_running=not args.no_attach,
        allow_launch=not args.no_launch,
        timeout_seconds=300.0,
    )
    result = execute_cad_transfer_v1(
        sketch_package=sketch_package,
        adapter=SolidWorksAgentAdapter(config),
        cad_package_id="CAD-SW-GOLDEN-001",
        report_id="CADV-SW-GOLDEN-001",
    )

    cad_package_path = args.output_dir / "cad_package.json"
    report_path = args.output_dir / "cad_verification.json"
    cad_package_path.write_text(json.dumps(result.cad_package, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(result.cad_verification_report, indent=2), encoding="utf-8")

    statuses = [item["status"] for item in result.cad_verification_report["items"]]
    print(json.dumps(result.cad_verification_report, indent=2))
    if statuses != ["VERIFIED", "VERIFIED", "VERIFIED", "VERIFIED"]:
        print("CANONICAL_CAD_VERIFICATION=FAILED", file=sys.stderr)
        return 40
    if result.cad_verification_report["overall_status"] != "VERIFIED":
        print("CANONICAL_CAD_VERIFICATION=FAILED", file=sys.stderr)
        return 40

    print("CANONICAL_CAD_VERIFICATION=VERIFIED")
    print("FINAL_RUNTIME_STATUS=DEFERRED_TO_PRIMARY_CHAT_4")
    print(f"CAD_PACKAGE={cad_package_path}")
    print(f"CAD_VERIFICATION={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
