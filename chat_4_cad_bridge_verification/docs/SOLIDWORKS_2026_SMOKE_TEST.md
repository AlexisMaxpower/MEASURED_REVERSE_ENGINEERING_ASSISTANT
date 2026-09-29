# SOLIDWORKS 2026 real-host smoke / golden procedure

**Status in ChatGPT execution environment:** `UNVERIFIED` — no Windows 11 + SOLIDWORKS 2026 COM host is available here.

## Required host

- Windows 11 x64
- SOLIDWORKS 2026 x64 installed and launchable in the interactive user session
- Python able to run Chat 4 package/tests
- Visual Studio Build Tools / MSBuild capable of targeting .NET Framework 4.8
- local official SOLIDWORKS API interop assemblies

## 1. Build the agent

From the repository:

```powershell
cd chat_4_cad_bridge_verification
.\scripts\build_solidworks_agent.ps1 -SolidWorksInstallDir "C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"
```

If SOLIDWORKS is installed elsewhere, pass that installation directory. The script expects the official interop assemblies in `api\redist` and does not copy them into the repository.

## 2. Run ordinary tests first

```powershell
python -m pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD\src"
python -m unittest discover -s tests -v
```

These tests must not require SOLIDWORKS.

## 3. Run the real golden transfer

```powershell
.\scripts\run_solidworks_golden.ps1 `
  -Agent ".\solidworks_agent\bin\Release\Mrea.SolidWorksCadAgent.exe" `
  -OutputDir ".\artifacts\solidworks-golden"
```

Optional explicit template:

```powershell
-PartTemplate "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\Part.prtdot"
```

## Expected acceptance

The script must finish with:

```text
REAL_HOST_RESULT=VERIFIED
```

and the canonical report must contain, in canonical order:

```text
D-WIDTH   80.2 mm  VERIFIED
D-HEIGHT  42.1 mm  VERIFIED
D-HOLE     5.1 mm  VERIFIED
D-CENTER  60.0 mm  VERIFIED
overall_status = VERIFIED
```

The output directory must also contain a native `.SLDPRT`, `cad_package.json`, and `cad_verification.json`.

## Failure semantics

Any of the following means the real-host gate is **not verified**:

- agent cannot attach/launch SOLIDWORKS;
- FRONT plane cannot be identified/selected;
- entity or verified dimension cannot be created;
- native part cannot be saved;
- dimension mapping/read-back is missing;
- any verification item is `MISMATCH`, `MISSING`, or `CONSTRAINT_CONFLICT`;
- process exits without `REAL_HOST_RESULT=VERIFIED`.

Do not manually edit the output report to turn a failed transfer into a pass.
