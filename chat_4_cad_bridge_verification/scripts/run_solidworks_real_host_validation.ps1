param(
    [Parameter(Mandatory=$true)]
    [string]$SolidWorksInstallDir,
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    [string]$Agent,
    [string]$PartTemplate,
    [switch]$NoAttach,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$preflight = Join-Path $PSScriptRoot "test_solidworks_host_readiness.ps1"
$builder = Join-Path $PSScriptRoot "build_solidworks_agent.ps1"
$runner = Join-Path $PSScriptRoot "run_solidworks_real_host_validation.py"
$outputFull = [IO.Path]::GetFullPath($OutputDir)
[IO.Directory]::CreateDirectory($outputFull) | Out-Null

if (-not $Agent) {
    $Agent = Join-Path $root "solidworks_agent\bin\Release\Mrea.SolidWorksCadAgent.exe"
}
$agentFull = [IO.Path]::GetFullPath($Agent)
$prebuildReadiness = Join-Path $outputFull "host_readiness_prebuild.json"
$finalReadiness = Join-Path $outputFull "host_readiness.json"

$powerShellExe = Join-Path $PSHOME "powershell.exe"
if (-not (Test-Path -LiteralPath $powerShellExe -PathType Leaf)) {
    $powerShellCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if ($null -eq $powerShellCommand) { $powerShellCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue }
    if ($null -eq $powerShellCommand) {
        Write-Error "HOST_PREFLIGHT_NOT_READY: no child PowerShell executable is available."
        exit 10
    }
    $powerShellExe = $powerShellCommand.Source
}

function Invoke-Readiness {
    param(
        [string]$JsonPath,
        [bool]$AgentRequired,
        [bool]$RequireBuildTools
    )
    $childArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $preflight,
        "-SolidWorksInstallDir", $SolidWorksInstallDir,
        "-AgentPath", $agentFull,
        "-OutputDir", $outputFull,
        "-OutputJson", $JsonPath
    )
    if ($PartTemplate) { $childArgs += @("-PartTemplate", $PartTemplate) }
    if (-not $AgentRequired) { $childArgs += "-AgentOptional" }
    if ($RequireBuildTools) { $childArgs += "-RequireBuildTools" }
    if (-not $NoLaunch) { $childArgs += "-AllowLaunchForVersionProbe" }

    & $powerShellExe @childArgs
    return $LASTEXITCODE
}

function Invoke-AgentBuild {
    $childArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $builder,
        "-SolidWorksInstallDir", $SolidWorksInstallDir,
        "-Configuration", "Release"
    )
    & $powerShellExe @childArgs
    return $LASTEXITCODE
}

try {
    if (-not (Test-Path -LiteralPath $agentFull -PathType Leaf)) {
        Write-Host "CAD Agent not found. Running preliminary host/build readiness..."
        $preExit = Invoke-Readiness -JsonPath $prebuildReadiness -AgentRequired $false -RequireBuildTools $true
        if ($preExit -ne 0) {
            Write-Error "HOST_PREFLIGHT_NOT_READY: preliminary readiness is not READY. See $prebuildReadiness"
            exit 10
        }

        Write-Host "Building SOLIDWORKS CAD Agent..."
        $buildExit = Invoke-AgentBuild
        if ($buildExit -ne 0) {
            Write-Error "HOST_BUILD_NOT_READY: CAD Agent build failed with exit $buildExit."
            exit 10
        }
    }

    Write-Host "Running final fail-closed host readiness..."
    $readyExit = Invoke-Readiness -JsonPath $finalReadiness -AgentRequired $true -RequireBuildTools $false
    if ($readyExit -ne 0) {
        Write-Error "HOST_PREFLIGHT_NOT_READY: final readiness is not READY. See $finalReadiness"
        exit 10
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -eq $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
    if ($null -eq $python) {
        Write-Error "HOST_PREFLIGHT_NOT_READY: Python executable is unavailable."
        exit 10
    }

    $env:PYTHONPATH = Join-Path $root "src"
    $argsList = @(
        $runner,
        "--agent", $agentFull,
        "--output-dir", $outputFull,
        "--host-readiness", $finalReadiness
    )
    if ($PartTemplate) { $argsList += @("--part-template", $PartTemplate) }
    if ($NoAttach) { $argsList += "--no-attach" }
    if ($NoLaunch) { $argsList += "--no-launch" }

    Write-Host "Running controlled SOLIDWORKS transfer and runtime-evidence gate..."
    & $python.Source @argsList
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        exit $code
    }

    Write-Host "REAL_HOST_GATE=VERIFIED"
    Write-Host "HOST_READINESS=$finalReadiness"
    exit 0
} catch {
    Write-Error ("REAL_HOST_GATE_INTERNAL_FAILURE: " + $_.Exception.Message)
    exit 70
}
