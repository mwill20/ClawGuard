param(
    [string]$Remote = "root@31.97.139.139",
    [string]$RemoteDir = "/docker/openclaw-utxu/data/clawguard/telemetry",
    [string]$OutputDir = "lessons/telemetry",
    [string[]]$Sessions = @(),
    [switch]$Latest,
    [switch]$DryRun,
    [string[]]$ProfileString = @(),
    [string[]]$ExtraPattern = @()
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$sessionList = @($Sessions | Where-Object { $_ })
if ($sessionList.Count -eq 0) {
    $Latest = $true
}

if ($DryRun) {
    Write-Host "DRY RUN: would pull ClawGuard telemetry"
    Write-Host "  remote: $Remote"
    Write-Host "  remote_dir: $RemoteDir"
    if ($Latest) {
        Write-Host "  latest_json: ${Remote}:${RemoteDir}/telemetry_latest.json"
        Write-Host "  latest_md: ${Remote}:${RemoteDir}/telemetry_latest.md"
    }
    foreach ($session in $sessionList) {
        Write-Host "  session_json: ${Remote}:${RemoteDir}/telemetry_*_${session}.json"
        Write-Host "  session_md: ${Remote}:${RemoteDir}/telemetry_*_${session}.md"
    }
    Write-Host "DRY RUN: would redact, validate, and export to $OutputDir"
    exit 0
}

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("clawguard-telemetry-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    if ($Latest) {
        scp "${Remote}:${RemoteDir}/telemetry_latest.json" $tempDir
        scp "${Remote}:${RemoteDir}/telemetry_latest.md" $tempDir
    }

    foreach ($session in $sessionList) {
        scp "${Remote}:${RemoteDir}/telemetry_*_${session}.json" $tempDir
        scp "${Remote}:${RemoteDir}/telemetry_*_${session}.md" $tempDir
    }

    $pythonArgs = @(
        "-B",
        "scripts\export_telemetry.py",
        "--input-dir",
        $tempDir,
        "--output-dir",
        $OutputDir
    )
    foreach ($session in $sessionList) {
        $pythonArgs += "--session"
        $pythonArgs += $session
    }
    foreach ($value in $ProfileString) {
        $pythonArgs += "--profile-string"
        $pythonArgs += $value
    }
    foreach ($pattern in $ExtraPattern) {
        $pythonArgs += "--extra-pattern"
        $pythonArgs += $pattern
    }

    python @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "scripts\export_telemetry.py failed with exit code $LASTEXITCODE"
    }
}
finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
