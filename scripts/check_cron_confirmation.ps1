param(
    [string]$Remote = "root@31.97.139.139",
    [string]$LogDir = "/docker/openclaw-utxu/data/clawguard/logs",
    [string]$TelemetryDir = "/docker/openclaw-utxu/data/clawguard/telemetry",
    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),
    [string]$TempDir = (Join-Path $env:TEMP "clawguard-telemetry"),
    [switch]$SkipTelemetryValidation,
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

$remoteScript = @"
set -u
LOG_DIR=$(ConvertTo-ShellLiteral $LogDir)
TELEMETRY_DIR=$(ConvertTo-ShellLiteral $TelemetryDir)
DATE_VALUE=$(ConvertTo-ShellLiteral $Date)
PATTERN='ClawGuard ASI06 detector module active'
TELEMETRY_JSON="`$TELEMETRY_DIR/telemetry_latest.json"
TELEMETRY_MD="`$TELEMETRY_DIR/telemetry_latest.md"

echo "== ClawGuard cron confirmation (`$DATE_VALUE) =="
echo ""
echo "== Detector module log check =="
if grep -H "`$PATTERN" "`$LOG_DIR"/*_"`$DATE_VALUE".log "`$LOG_DIR"/cron.log 2>/dev/null; then
  DETECTOR_OK=1
else
  DETECTOR_OK=0
  echo "MISSING: `$PATTERN"
fi

echo ""
echo "== Compile log tail =="
if [ -f "`$LOG_DIR/compile_`$DATE_VALUE.log" ]; then
  tail -40 "`$LOG_DIR/compile_`$DATE_VALUE.log"
else
  echo "missing `$LOG_DIR/compile_`$DATE_VALUE.log"
fi

echo ""
echo "== Post-compile log tail =="
if [ -f "`$LOG_DIR/post_compile_`$DATE_VALUE.log" ]; then
  tail -40 "`$LOG_DIR/post_compile_`$DATE_VALUE.log"
else
  echo "missing `$LOG_DIR/post_compile_`$DATE_VALUE.log"
fi

echo ""
echo "== telemetry_latest.md =="
if [ -f "`$TELEMETRY_MD" ]; then
  stat -c '%y %n' "`$TELEMETRY_MD"
  cat "`$TELEMETRY_MD"
else
  echo "missing `$TELEMETRY_MD"
fi

if [ "`$DETECTOR_OK" -eq 1 ]; then
  echo "__CLAWGUARD_DETECTOR_OK=1"
else
  echo "__CLAWGUARD_DETECTOR_OK=0"
fi
"@

if ($DryRun) {
    Write-Host "Remote target: $Remote"
    Write-Host "Remote transport: scp temp script, then ssh -o BatchMode=yes $Remote bash /tmp/<script>"
    Write-Host "Remote script:"
    Write-Host $remoteScript
    Write-Host ""
    Write-Host "Dry run complete."
    exit 0
}

Write-Host "Checking OpenClaw cron confirmation on $Remote for $Date..."
Write-Host ""

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
$localScript = Join-Path $TempDir "clawguard_cron_confirmation_$PID.sh"
$remoteScriptPath = "/tmp/clawguard_cron_confirmation_$PID.sh"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $localScript,
    (($remoteScript -replace "`r`n", "`n") + "`n"),
    $utf8NoBom
)

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $scpOutput = & scp $localScript "${Remote}:$remoteScriptPath" 2>&1
    $scpExit = $LASTEXITCODE
    if ($scpExit -ne 0) {
        $scpOutput | ForEach-Object { Write-Host $_.ToString() }
        throw "scp failed with exit code $scpExit"
    }

    $remoteRunCommand = "bash $remoteScriptPath; rc=`$?; rm -f $remoteScriptPath; exit `$rc"
    $output = & ssh -o BatchMode=yes $Remote $remoteRunCommand 2>&1
    $sshExit = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
    if (Test-Path -LiteralPath $localScript) {
        Remove-Item -LiteralPath $localScript -Force
    }
}

$outputText = @()
$output | ForEach-Object {
    if ($_ -is [System.Management.Automation.ErrorRecord]) {
        $line = $_.Exception.Message
    }
    else {
        $line = $_.ToString()
    }
    $line = $line -replace "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted-email]"
    $outputText += $line
    Write-Host $line
}
if ($sshExit -ne 0) {
    throw "ssh check failed with exit code $sshExit"
}

$detectorConfirmed = $outputText -match "__CLAWGUARD_DETECTOR_OK=1"
if (-not $detectorConfirmed) {
    throw "Detector module confirmation line was not found. Keep the inline fallback and inspect the cron logs."
}

if (-not $SkipTelemetryValidation) {
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
    $localJson = Join-Path $TempDir "telemetry_latest.json"
    $remoteJson = "${Remote}:${TelemetryDir}/telemetry_latest.json"

    Write-Host ""
    Write-Host "== Pull and validate telemetry_latest.json =="
    Invoke-Native "scp" @($remoteJson, $localJson)
    Invoke-Native "python" @(
        "-B",
        "scripts\validate_telemetry.py",
        "--input",
        $localJson
    )
}

Write-Host ""
Write-Host "Cron confirmation passed. Detector-backed ASI06 path is active."
