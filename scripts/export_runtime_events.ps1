param(
    [string]$Remote = "root@31.97.139.139",
    [string]$HostDataDir = "/docker/openclaw-utxu/data/clawguard",
    [string]$RemoteDir = "/docker/openclaw-utxu/data/clawguard/runtime_events",
    [string]$RedactedDir = "/docker/openclaw-utxu/data/clawguard/runtime_events_redacted",
    [string]$OutputDir = "lessons/runtime-events",
    [string[]]$Sessions = @(),
    [switch]$Latest,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function ConvertTo-ShellLiteral {
    param([string]$Value)
    return "'" + ($Value -replace "'", "'\''") + "'"
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

$sessionList = @($Sessions | Where-Object { $_ })
if ($sessionList.Count -eq 0) {
    $Latest = $true
}

$redactorPath = "${HostDataDir}/clawguard_redact_runtime_events.py"
$redactorArgs = @(
    "--input-dir", (ConvertTo-ShellLiteral $RemoteDir),
    "--output-dir", (ConvertTo-ShellLiteral $RedactedDir)
)
if ($Latest) {
    $redactorArgs += "--latest"
}
foreach ($session in $sessionList) {
    $redactorArgs += "--session"
    $redactorArgs += (ConvertTo-ShellLiteral $session)
}

$remoteRedactionCommand = "python3 " + (ConvertTo-ShellLiteral $redactorPath) + " " + ($redactorArgs -join " ")

if ($DryRun) {
    Write-Host "DRY RUN: would redact ClawGuard runtime events on host"
    Write-Host "  remote: $Remote"
    Write-Host "  redactor: $redactorPath"
    Write-Host "  input_dir: $RemoteDir"
    Write-Host "  redacted_dir: $RedactedDir"
    Write-Host "  command: $remoteRedactionCommand"
    if ($Latest) {
        Write-Host "  pull: ${Remote}:${RedactedDir}/runtime_events_latest.redacted.json"
    }
    foreach ($session in $sessionList) {
        Write-Host "  pull: ${Remote}:${RedactedDir}/runtime_events_*_${session}.redacted.json"
    }
    Write-Host "DRY RUN: would validate redaction status and runtime-events schema before writing to $OutputDir"
    exit 0
}

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("clawguard-runtime-events-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    Invoke-Native "ssh" @("-o", "BatchMode=yes", $Remote, $remoteRedactionCommand)

    if ($Latest) {
        Invoke-Native "scp" @("${Remote}:${RedactedDir}/runtime_events_latest.redacted.json", $tempDir)
    }
    foreach ($session in $sessionList) {
        Invoke-Native "scp" @("${Remote}:${RedactedDir}/runtime_events_*_${session}.redacted.json", $tempDir)
    }

    $files = @(Get-ChildItem -LiteralPath $tempDir -Filter "*.redacted.json" -File)
    if ($files.Count -eq 0) {
        throw "No redacted runtime-event artifacts were pulled"
    }

    foreach ($file in $files) {
        Invoke-Native "python" @("-B", "scripts\validate_runtime_events.py", "--input", $file.FullName)
        $json = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        if (-not $json.PSObject.Properties.Name.Contains("redaction")) {
            throw "$($file.FullName) missing host redaction metadata"
        }
        if ($json.redaction.status -ne "host_redacted") {
            throw "$($file.FullName) missing host redaction status"
        }
        Write-Host "redaction_status=host_redacted $($file.Name)"
    }

    $pythonArgs = @(
        "-B",
        "scripts\export_runtime_events.py",
        "--input-dir",
        $tempDir,
        "--output-dir",
        $OutputDir
    )
    foreach ($session in $sessionList) {
        $pythonArgs += "--session"
        $pythonArgs += $session
    }
    python @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "scripts\export_runtime_events.py failed with exit code $LASTEXITCODE"
    }
}
finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
