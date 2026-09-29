param(
    [Parameter(Mandatory=$true)]
    [string]$SolidWorksInstallDir,
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root "solidworks_agent\Mrea.SolidWorksCadAgent.csproj"
$interop = Join-Path $SolidWorksInstallDir "api\redist"

function Find-MsBuild {
    $command = Get-Command msbuild.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }

    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path -LiteralPath $vswhere -PathType Leaf) {
        $matches = @(& $vswhere -latest -products * -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" 2>$null)
        $candidate = $matches | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
        if ($candidate) { return [string]$candidate }
    }
    return $null
}

$sldworks = Join-Path $interop "SolidWorks.Interop.sldworks.dll"
$swconst = Join-Path $interop "SolidWorks.Interop.swconst.dll"
if (-not (Test-Path -LiteralPath $sldworks -PathType Leaf)) {
    Write-Error "HOST_BUILD_NOT_READY: missing $sldworks"
    exit 10
}
if (-not (Test-Path -LiteralPath $swconst -PathType Leaf)) {
    Write-Error "HOST_BUILD_NOT_READY: missing $swconst"
    exit 10
}

$msbuild = Find-MsBuild
if (-not $msbuild) {
    Write-Error "HOST_BUILD_NOT_READY: MSBuild was not found in PATH or through Visual Studio Installer/vswhere."
    exit 10
}

& $msbuild $project /t:Build /p:Configuration=$Configuration /p:Platform=x64 /p:SolidWorksInteropDir="$interop"
if ($LASTEXITCODE -ne 0) {
    Write-Error "HOST_BUILD_NOT_READY: MSBuild failed with exit $LASTEXITCODE."
    exit 10
}

$artifact = Join-Path $root "solidworks_agent\bin\$Configuration\Mrea.SolidWorksCadAgent.exe"
if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
    Write-Error "HOST_BUILD_NOT_READY: build completed without expected agent executable $artifact"
    exit 10
}

Write-Host "Built: $artifact"
exit 0
