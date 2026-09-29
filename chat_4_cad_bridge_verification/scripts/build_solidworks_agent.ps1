param(
    [Parameter(Mandatory=$true)]
    [string]$SolidWorksInstallDir,
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$project = Join-Path $root "solidworks_agent\Mrea.SolidWorksCadAgent.csproj"
$interop = Join-Path $SolidWorksInstallDir "api\redist"

$sldworks = Join-Path $interop "SolidWorks.Interop.sldworks.dll"
$swconst = Join-Path $interop "SolidWorks.Interop.swconst.dll"
if (-not (Test-Path $sldworks)) { throw "Missing $sldworks" }
if (-not (Test-Path $swconst)) { throw "Missing $swconst" }

$msbuild = Get-Command msbuild.exe -ErrorAction Stop
& $msbuild.Source $project /t:Build /p:Configuration=$Configuration /p:Platform=x64 /p:SolidWorksInteropDir="$interop"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Built: $(Join-Path $root "solidworks_agent\bin\$Configuration\Mrea.SolidWorksCadAgent.exe")"
