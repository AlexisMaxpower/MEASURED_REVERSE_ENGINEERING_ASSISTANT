param(
    [Parameter(Mandatory=$true)]
    [string]$Agent,
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    [string]$PartTemplate
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $root "src"
$argsList = @(
    (Join-Path $PSScriptRoot "run_solidworks_golden.py"),
    "--agent", $Agent,
    "--output-dir", $OutputDir
)
if ($PartTemplate) {
    $argsList += @("--part-template", $PartTemplate)
}
python @argsList
exit $LASTEXITCODE
