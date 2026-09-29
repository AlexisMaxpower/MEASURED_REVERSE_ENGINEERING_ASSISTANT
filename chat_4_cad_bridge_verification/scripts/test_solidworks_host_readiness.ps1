param(
    [Parameter(Mandatory=$true)]
    [string]$SolidWorksInstallDir,
    [Parameter(Mandatory=$true)]
    [string]$AgentPath,
    [Parameter(Mandatory=$true)]
    [string]$OutputDir,
    [Parameter(Mandatory=$true)]
    [string]$OutputJson,
    [string]$PartTemplate,
    [switch]$AgentOptional,
    [switch]$RequireBuildTools,
    [switch]$AllowLaunchForVersionProbe
)

$ErrorActionPreference = "Stop"
$AdapterName = "SOLIDWORKS_2026"
$ExpectedRevisionMajor = 34
$agentIsRequired = -not $AgentOptional
$checks = New-Object System.Collections.Generic.List[object]

function Add-ReadinessCheck {
    param(
        [string]$Code,
        [ValidateSet("PASS","FAIL","UNVERIFIED")]
        [string]$Status,
        [string]$Message,
        [bool]$Required = $true,
        [hashtable]$Details = $null
    )
    $item = [ordered]@{
        code = $Code
        status = $Status
        message = $Message
        required = $Required
    }
    if ($null -ne $Details -and $Details.Count -gt 0) {
        $item.details = $Details
    }
    $checks.Add([pscustomobject]$item) | Out-Null
}

function Get-AggregateStatus {
    param([System.Collections.Generic.List[object]]$Items)
    $required = @($Items | Where-Object { $_.required -eq $true })
    if (@($required | Where-Object { $_.status -eq "FAIL" }).Count -gt 0) {
        return "FAILED"
    }
    if (@($required | Where-Object { $_.status -eq "UNVERIFIED" }).Count -gt 0) {
        return "UNVERIFIED"
    }
    return "READY"
}

function Write-JsonUtf8NoBom {
    param([string]$Path, [object]$Value)
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { [IO.Directory]::CreateDirectory($parent) | Out-Null }
    $json = $Value | ConvertTo-Json -Depth 10
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($Path), $json, (New-Object Text.UTF8Encoding($false)))
}

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

try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $isWin11 = [string]$os.Caption -match "Windows 11"
    $isOs64 = [string]$os.OSArchitecture -match "64"
    if ($isWin11 -and $isOs64) {
        Add-ReadinessCheck "OS_WINDOWS_11_X64" "PASS" "Windows 11 x64 detected." $true @{
            caption = [string]$os.Caption
            version = [string]$os.Version
            architecture = [string]$os.OSArchitecture
        }
    } else {
        Add-ReadinessCheck "OS_WINDOWS_11_X64" "FAIL" "Windows 11 x64 is required." $true @{
            caption = [string]$os.Caption
            version = [string]$os.Version
            architecture = [string]$os.OSArchitecture
        }
    }
} catch {
    Add-ReadinessCheck "OS_WINDOWS_11_X64" "UNVERIFIED" "Could not query Windows operating-system identity." $true @{
        error = $_.Exception.Message
    }
}

if ([Environment]::Is64BitProcess) {
    Add-ReadinessCheck "PROCESS_X64" "PASS" "Host preflight is running in a 64-bit process." $true @{
        process_architecture = "x64"
    }
} else {
    Add-ReadinessCheck "PROCESS_X64" "FAIL" "A 64-bit PowerShell process is required." $true @{
        process_architecture = "x86"
    }
}

try {
    $net = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" -Name Release -ErrorAction Stop
    $release = [int]$net.Release
    if ($release -ge 528040) {
        Add-ReadinessCheck "DOTNET_FRAMEWORK_48" "PASS" ".NET Framework 4.8 or later 4.x release detected." $true @{
            release = $release
        }
    } else {
        Add-ReadinessCheck "DOTNET_FRAMEWORK_48" "FAIL" ".NET Framework 4.8 is required." $true @{
            release = $release
            minimum_release = 528040
        }
    }
} catch {
    Add-ReadinessCheck "DOTNET_FRAMEWORK_48" "UNVERIFIED" "Could not verify .NET Framework 4.8." $true @{
        error = $_.Exception.Message
    }
}

if ($RequireBuildTools) {
    $msbuild = Find-MsBuild
    if ($msbuild) {
        Add-ReadinessCheck "MSBUILD_AVAILABLE" "PASS" "MSBuild is available for the .NET Framework agent build." $true @{
            path = $msbuild
        }
    } else {
        Add-ReadinessCheck "MSBUILD_AVAILABLE" "FAIL" "MSBuild is required because the CAD Agent executable is not available." $true
    }
}

$agentFullPath = [IO.Path]::GetFullPath($AgentPath)
if (Test-Path -LiteralPath $agentFullPath -PathType Leaf) {
    Add-ReadinessCheck "AGENT_EXECUTABLE_AVAILABLE" "PASS" "CAD Agent executable is available." $agentIsRequired @{
        path = $agentFullPath
    }
} else {
    $agentStatus = if ($agentIsRequired) { "FAIL" } else { "UNVERIFIED" }
    Add-ReadinessCheck "AGENT_EXECUTABLE_AVAILABLE" $agentStatus "CAD Agent executable is not available yet." $agentIsRequired @{
        path = $agentFullPath
    }
}

$interopDir = Join-Path ([IO.Path]::GetFullPath($SolidWorksInstallDir)) "api\redist"
$sldworksInterop = Join-Path $interopDir "SolidWorks.Interop.sldworks.dll"
$swconstInterop = Join-Path $interopDir "SolidWorks.Interop.swconst.dll"
$interopPresent = (Test-Path -LiteralPath $sldworksInterop -PathType Leaf) -and (Test-Path -LiteralPath $swconstInterop -PathType Leaf)
if ($interopPresent) {
    Add-ReadinessCheck "SOLIDWORKS_INTEROP_AVAILABLE" "PASS" "Official SOLIDWORKS API interop assemblies are available." $true @{
        interop_directory = $interopDir
        sldworks = $sldworksInterop
        swconst = $swconstInterop
    }
} else {
    Add-ReadinessCheck "SOLIDWORKS_INTEROP_AVAILABLE" "FAIL" "Required SOLIDWORKS interop assemblies are missing." $true @{
        interop_directory = $interopDir
        sldworks_exists = (Test-Path -LiteralPath $sldworksInterop -PathType Leaf)
        swconst_exists = (Test-Path -LiteralPath $swconstInterop -PathType Leaf)
    }
}

$comType = $null
try {
    $comType = [Type]::GetTypeFromProgID("SldWorks.Application", $false)
    if ($null -ne $comType) {
        Add-ReadinessCheck "SOLIDWORKS_COM_REGISTERED" "PASS" "SldWorks.Application COM ProgID is registered." $true @{
            prog_id = "SldWorks.Application"
        }
    } else {
        Add-ReadinessCheck "SOLIDWORKS_COM_REGISTERED" "FAIL" "SldWorks.Application COM ProgID is not registered." $true
    }
} catch {
    Add-ReadinessCheck "SOLIDWORKS_COM_REGISTERED" "UNVERIFIED" "Could not query SOLIDWORKS COM registration." $true @{
        error = $_.Exception.Message
    }
}

try {
    $outputFullPath = [IO.Path]::GetFullPath($OutputDir)
    [IO.Directory]::CreateDirectory($outputFullPath) | Out-Null
    $probe = Join-Path $outputFullPath (".mrea-write-probe-" + [Guid]::NewGuid().ToString("N") + ".tmp")
    [IO.File]::WriteAllText($probe, "mrea", (New-Object Text.UTF8Encoding($false)))
    Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
    Add-ReadinessCheck "OUTPUT_PATH_WRITABLE" "PASS" "Artifact output directory is writable." $true @{
        path = $outputFullPath
    }
} catch {
    Add-ReadinessCheck "OUTPUT_PATH_WRITABLE" "FAIL" "Artifact output directory is not writable." $true @{
        path = $OutputDir
        error = $_.Exception.Message
    }
}

$swApp = $null
$launchedForProbe = $false
try {
    try {
        $swApp = [Runtime.InteropServices.Marshal]::GetActiveObject("SldWorks.Application")
    } catch {
        $swApp = $null
    }

    if ($null -eq $swApp -and $AllowLaunchForVersionProbe -and $null -ne $comType) {
        $swApp = [Activator]::CreateInstance($comType)
        $launchedForProbe = $true
        try { $swApp.Visible = $false } catch { }
    }

    if ($null -ne $swApp) {
        $revision = [string]$swApp.RevisionNumber()
        $majorText = ($revision -split '\.')[0]
        $major = 0
        if ([int]::TryParse($majorText, [ref]$major)) {
            if ($major -eq $ExpectedRevisionMajor) {
                Add-ReadinessCheck "SOLIDWORKS_VERSION_2026" "PASS" "Running/probed SOLIDWORKS revision is compatible with the 2026 adapter." $true @{
                    revision_number = $revision
                    revision_major = $major
                    expected_revision_major = $ExpectedRevisionMajor
                }
            } else {
                Add-ReadinessCheck "SOLIDWORKS_VERSION_2026" "FAIL" "SOLIDWORKS revision does not match the 2026 adapter baseline." $true @{
                    revision_number = $revision
                    revision_major = $major
                    expected_revision_major = $ExpectedRevisionMajor
                }
            }
        } else {
            Add-ReadinessCheck "SOLIDWORKS_VERSION_2026" "UNVERIFIED" "SOLIDWORKS RevisionNumber could not be parsed." $true @{
                revision_number = $revision
            }
        }
    } else {
        Add-ReadinessCheck "SOLIDWORKS_VERSION_2026" "UNVERIFIED" "No running SOLIDWORKS session was available and launch-for-probe was not enabled." $true
    }

    if ($PartTemplate) {
        $templateFullPath = [IO.Path]::GetFullPath($PartTemplate)
        if (Test-Path -LiteralPath $templateFullPath -PathType Leaf) {
            Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "PASS" "Explicit SOLIDWORKS part template is available." $true @{
                path = $templateFullPath
                source = "explicit"
            }
        } else {
            Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "FAIL" "Explicit SOLIDWORKS part template does not exist." $true @{
                path = $templateFullPath
                source = "explicit"
            }
        }
    } elseif ($null -ne $swApp -and $interopPresent) {
        try {
            [Reflection.Assembly]::LoadFrom($swconstInterop) | Out-Null
            $preference = [int][SolidWorks.Interop.swconst.swUserPreferenceStringValue_e]::swDefaultTemplatePart
            $defaultTemplate = [string]$swApp.GetUserPreferenceStringValue($preference)
            if ($defaultTemplate -and (Test-Path -LiteralPath $defaultTemplate -PathType Leaf)) {
                Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "PASS" "Configured default SOLIDWORKS part template is available." $true @{
                    path = $defaultTemplate
                    source = "solidworks_default"
                }
            } else {
                Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "FAIL" "SOLIDWORKS default part template is not configured or does not exist." $true @{
                    path = $defaultTemplate
                    source = "solidworks_default"
                }
            }
        } catch {
            Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "UNVERIFIED" "Could not query the SOLIDWORKS default part template." $true @{
                error = $_.Exception.Message
            }
        }
    } else {
        Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "UNVERIFIED" "No explicit template was supplied and the SOLIDWORKS default template could not be queried." $true
    }
} catch {
    if (-not (@($checks | Where-Object { $_.code -eq "SOLIDWORKS_VERSION_2026" }).Count)) {
        Add-ReadinessCheck "SOLIDWORKS_VERSION_2026" "UNVERIFIED" "SOLIDWORKS version probe failed." $true @{
            error = $_.Exception.Message
        }
    }
    if (-not (@($checks | Where-Object { $_.code -eq "PART_TEMPLATE_AVAILABLE" }).Count)) {
        Add-ReadinessCheck "PART_TEMPLATE_AVAILABLE" "UNVERIFIED" "SOLIDWORKS part-template probe failed." $true @{
            error = $_.Exception.Message
        }
    }
} finally {
    if ($null -ne $swApp) {
        if ($launchedForProbe) {
            try { $swApp.ExitApp() } catch { }
        }
        try { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($swApp) | Out-Null } catch { }
        $swApp = $null
    }
}

$status = Get-AggregateStatus $checks
$report = [ordered]@{
    schema_version = "mrea.cad-host-readiness.v1"
    adapter_name = $AdapterName
    status = $status
    checks = @($checks)
}

Write-JsonUtf8NoBom $OutputJson $report
$report | ConvertTo-Json -Depth 10

if ($status -eq "READY") { exit 0 }
exit 10
