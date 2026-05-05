param(
    [string]$Remote = "root@31.97.139.139",
    [string]$RemoteDir = "/docker/openclaw-utxu/data/clawguard/telemetry",
    [string]$OutputDir = "lessons/telemetry",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

& (Join-Path $PSScriptRoot "export_telemetry.ps1") `
    -Remote $Remote `
    -RemoteDir $RemoteDir `
    -OutputDir $OutputDir `
    -Latest `
    -DryRun:$DryRun
