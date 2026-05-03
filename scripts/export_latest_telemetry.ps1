param(
    [string]$Remote = "root@31.97.139.139",
    [string]$RemoteDir = "/docker/openclaw-utxu/data/clawguard/telemetry",
    [string]$OutputDir = "lessons/telemetry"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$latestJson = Join-Path $OutputDir "telemetry_latest.json"
$latestMd = Join-Path $OutputDir "telemetry_latest.md"

scp "${Remote}:${RemoteDir}/telemetry_latest.json" $latestJson
scp "${Remote}:${RemoteDir}/telemetry_latest.md" $latestMd

$telemetry = Get-Content -Raw -Path $latestJson | ConvertFrom-Json
$session = if ($telemetry.agent_session_id) { $telemetry.agent_session_id } else { "no-session" }
$digestPath = if ($telemetry.digest_path) { $telemetry.digest_path } else { "" }
$digestName = if ($digestPath) { [System.IO.Path]::GetFileNameWithoutExtension($digestPath) } else { "digest_unknown" }
$date = $digestName -replace '^digest_', ''

Copy-Item -Force -Path $latestJson -Destination (Join-Path $OutputDir "telemetry_${date}_${session}.json")
Copy-Item -Force -Path $latestMd -Destination (Join-Path $OutputDir "telemetry_${date}_${session}.md")

Write-Host "Exported ClawGuard telemetry:"
Write-Host "  session: $session"
Write-Host "  finding_count: $($telemetry.finding_count)"
Write-Host "  output_dir: $OutputDir"
