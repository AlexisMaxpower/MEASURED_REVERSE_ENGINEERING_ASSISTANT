param(
    [string]$SolidWorksInstallDir,
    [string]$OutputDir = ".\artifacts\solidworks-host-qualification",
    [string]$PartTemplate,
    [switch]$NoAttach,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $root
$preflight = Join-Path $PSScriptRoot "test_solidworks_host_readiness.ps1"
$builder = Join-Path $PSScriptRoot "build_solidworks_agent.ps1"
$hostValidation = Join-Path $PSScriptRoot "run_solidworks_pass3_host_validation.ps1"
$finalizer = Join-Path $PSScriptRoot "finalize_solidworks_qualification.py"
$agent = Join-Path $root "solidworks_agent\bin\Release\Mrea.SolidWorksCadAgent.exe"
$sketchFixture = Join-Path $repoRoot "tests\fixtures\contracts\sketch_package_v1.json"
$outputFull = [IO.Path]::GetFullPath($OutputDir)
[IO.Directory]::CreateDirectory($outputFull) | Out-Null

function Resolve-SolidWorksInstallDir {
    param([string]$Explicit)

    if ($Explicit) {
        $candidate = [IO.Path]::GetFullPath($Explicit)
        if (Test-Path -LiteralPath (Join-Path $candidate "api\redist\SolidWorks.Interop.sldworks.dll") -PathType Leaf) {
            return $candidate
        }
        throw "SOLIDWORKS_INSTALL_NOT_FOUND: explicit path does not contain api\redist\SolidWorks.Interop.sldworks.dll: $candidate"
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:ProgramFiles) {
        $candidates.Add((Join-Path $env:ProgramFiles "SOLIDWORKS Corp\SOLIDWORKS")) | Out-Null
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates.Add((Join-Path ${env:ProgramFiles(x86)} "SOLIDWORKS Corp\SOLIDWORKS")) | Out-Null
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate "api\redist\SolidWorks.Interop.sldworks.dll") -PathType Leaf) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }

    $roots = @()
    if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles "SOLIDWORKS Corp") }
    if (${env:ProgramFiles(x86)}) { $roots += (Join-Path ${env:ProgramFiles(x86)} "SOLIDWORKS Corp") }
    foreach ($searchRoot in $roots) {
        if (-not (Test-Path -LiteralPath $searchRoot -PathType Container)) { continue }
        $interop = Get-ChildItem -LiteralPath $searchRoot -Filter "SolidWorks.Interop.sldworks.dll" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\api\\redist\\SolidWorks\.Interop\.sldworks\.dll$" } |
            Select-Object -First 1
        if ($interop) {
            return [IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $interop.FullName))))
        }
    }

    throw "SOLIDWORKS_INSTALL_NOT_FOUND: pass -SolidWorksInstallDir or install SOLIDWORKS 2026 with API interop assemblies."
}

function Resolve-Python {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
    if ($null -eq $python) { throw "PYTHON_NOT_FOUND: python.exe/python is required." }
    return $python.Source
}

$installDir = Resolve-SolidWorksInstallDir -Explicit $SolidWorksInstallDir
$pythonExe = Resolve-Python
$prebuildReadiness = Join-Path $outputFull "qualification_prebuild_readiness.json"
$qualificationManifest = Join-Path $outputFull "solidworks_host_qualification.json"

Write-Host "SOLIDWORKS_INSTALL_DIR=$installDir"
Write-Host "Running build/readiness preflight against official SOLIDWORKS 2026 interop assemblies..."
$preflightArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $preflight,
    "-SolidWorksInstallDir", $installDir,
    "-AgentPath", $agent,
    "-OutputDir", $outputFull,
    "-OutputJson", $prebuildReadiness,
    "-AgentOptional",
    "-RequireBuildTools"
)
if ($PartTemplate) { $preflightArgs += @("-PartTemplate", $PartTemplate) }
if (-not $NoLaunch) { $preflightArgs += "-AllowLaunchForVersionProbe" }
& powershell.exe @preflightArgs
if ($LASTEXITCODE -ne 0) {
    throw "SOLIDWORKS_QUALIFICATION_PREFLIGHT_FAILED: exit=$LASTEXITCODE; evidence=$prebuildReadiness"
}

Write-Host "Building production x64 .NET Framework CAD Agent from source..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $builder -SolidWorksInstallDir $installDir -Configuration Release
if ($LASTEXITCODE -ne 0) {
    throw "SOLIDWORKS_QUALIFICATION_BUILD_FAILED: exit=$LASTEXITCODE"
}
if (-not (Test-Path -LiteralPath $agent -PathType Leaf)) {
    throw "SOLIDWORKS_QUALIFICATION_BUILD_FAILED: expected artifact missing: $agent"
}

Write-Host "Running controlled real-host transfer, native SLDPRT creation and canonical read-back..."
$hostArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $hostValidation,
    "-SolidWorksInstallDir", $installDir,
    "-OutputDir", $outputFull,
    "-Agent", $agent
)
if ($PartTemplate) { $hostArgs += @("-PartTemplate", $PartTemplate) }
if ($NoAttach) { $hostArgs += "-NoAttach" }
if ($NoLaunch) { $hostArgs += "-NoLaunch" }
& powershell.exe @hostArgs
if ($LASTEXITCODE -ne 0) {
    throw "SOLIDWORKS_QUALIFICATION_REAL_HOST_FAILED: exit=$LASTEXITCODE; evidence=$outputFull"
}

$runtimeInputs = Join-Path $outputFull "solidworks_runtime_inputs.json"
if (-not (Test-Path -LiteralPath $runtimeInputs -PathType Leaf)) {
    throw "SOLIDWORKS_QUALIFICATION_EVIDENCE_MISSING: $runtimeInputs"
}

$sourceCommit = if ($env:GITHUB_SHA) { $env:GITHUB_SHA } else { "LOCAL_WORKTREE" }
& $pythonExe $finalizer `
    --runtime-inputs $runtimeInputs `
    --prebuild-readiness $prebuildReadiness `
    --sketch-package $sketchFixture `
    --build-artifact $agent `
    --output $qualificationManifest `
    --source-commit $sourceCommit
if ($LASTEXITCODE -ne 0) {
    throw "SOLIDWORKS_QUALIFICATION_FINALIZATION_FAILED: exit=$LASTEXITCODE"
}

Write-Host ""
Write-Host "SOLIDWORKS_HOST_QUALIFICATION=VERIFIED"
Write-Host "PRODUCTION_CSHARP_INTEROP_BUILD=VERIFIED"
Write-Host "REAL_SOLIDWORKS_2026_HOST=VERIFIED"
Write-Host "NATIVE_SLDPRT_GENERATION_READBACK=VERIFIED"
Write-Host "QUALIFICATION_MANIFEST=$qualificationManifest"
