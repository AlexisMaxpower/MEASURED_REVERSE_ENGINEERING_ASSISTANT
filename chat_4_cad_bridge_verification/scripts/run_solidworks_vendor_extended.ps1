param(
    [Parameter(Mandatory=$true)]
    [string]$Agent,
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    [string]$PartTemplate
)

$ErrorActionPreference = "Stop"
$argsList = @(
    (Join-Path $PSScriptRoot "run_solidworks_vendor_extended.py"),
    "--agent", $Agent,
    "--output-dir", $OutputDir
)
if ($PartTemplate) {
    $argsList += @("--part-template", $PartTemplate)
}

python @argsList
exit $LASTEXITCODE
