param(
    [string]$Remote = "root@31.97.139.139",
    [string]$TelemetryMarkdownPath = "/docker/openclaw-utxu/data/clawguard/telemetry/telemetry_latest.md",
    [string]$Container = "openclaw-utxu-openclaw-1",
    [string]$DatabasePath = "/data/clawguard/jobs.db",
    [int]$Limit = 20
)

$ErrorActionPreference = "Stop"

function Quote-RemotePath {
    param([string]$Path)
    return "'" + ($Path -replace "'", "'\''") + "'"
}

$quotedTelemetryPath = Quote-RemotePath $TelemetryMarkdownPath

Write-Host "== ClawGuard telemetry_latest.md =="
ssh -o BatchMode=yes $Remote "stat -c '%y %n' $quotedTelemetryPath"
ssh -o BatchMode=yes $Remote "cat $quotedTelemetryPath"

Write-Host ""
Write-Host "== Latest job_security_findings rows =="

$sql = @"
.headers on
.mode column
SELECT
  COALESCE(agent_session_id, '') AS agent_session_id,
  rule_id,
  severity,
  COALESCE(json_extract(context, '$.source_platform'), '') AS source_platform,
  COALESCE(json_extract(context, '$.source_field'), '') AS source_field,
  COALESCE(json_extract(context, '$.job_title'), job_id) AS job_title,
  detected_at
FROM job_security_findings
ORDER BY detected_at DESC
LIMIT $Limit;
"@

$sql | ssh -o BatchMode=yes $Remote "docker exec -i $Container sqlite3 $DatabasePath"

Write-Host ""
Write-Host "Check complete."
