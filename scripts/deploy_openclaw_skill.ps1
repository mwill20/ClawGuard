param(
    [string]$Remote = "root@31.97.139.139",
    [string]$Container = "openclaw-utxu-openclaw-1",
    [string]$SkillDir = "/usr/local/lib/node_modules/openclaw/skills/job-search-custom",
    [string]$HostDataDir = "/docker/openclaw-utxu/data/clawguard",
    [string]$RemoteStageBase = "/tmp/clawguard-openclaw-deploy",
    [string]$TempDir = (Join-Path $env:TEMP "clawguard-openclaw-deploy"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$JobScript = Join-Path $RepoRoot "target-agent\skills\job-search-custom\job_search_secure.py"
$RuntimeEventsScript = Join-Path $RepoRoot "target-agent\skills\job-search-custom\runtime_events.py"
$RuntimeEventsRedactor = Join-Path $RepoRoot "target-agent\skills\job-search-custom\clawguard_redact_runtime_events.py"
$DetectionsDir = Join-Path $RepoRoot "detections"
$PostCompileHook = Join-Path $RepoRoot "target-agent\skills\job-search-custom\clawguard_post_compile.sh"
$CronScript = Join-Path $RepoRoot "target-agent\skills\job-search-custom\staggered_cron.sh"
$RemoteStage = "$RemoteStageBase-$PID"
if (-not $RemoteStage.StartsWith("/tmp/clawguard-openclaw-deploy-")) {
    throw "RemoteStage must stay under /tmp/clawguard-openclaw-deploy-*"
}

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

if (-not (Test-Path -LiteralPath $JobScript)) {
    throw "Missing runtime script: $JobScript"
}
if (-not (Test-Path -LiteralPath $RuntimeEventsScript)) {
    throw "Missing runtime-events writer: $RuntimeEventsScript"
}
if (-not (Test-Path -LiteralPath $RuntimeEventsRedactor)) {
    throw "Missing runtime-events redactor: $RuntimeEventsRedactor"
}
if (-not (Test-Path -LiteralPath $DetectionsDir)) {
    throw "Missing detections package: $DetectionsDir"
}
if (-not (Test-Path -LiteralPath $PostCompileHook)) {
    throw "Missing post-compile hook: $PostCompileHook"
}
if (-not (Test-Path -LiteralPath $CronScript)) {
    throw "Missing cron wrapper: $CronScript"
}

$quotedStage = ConvertTo-ShellLiteral $RemoteStage
$quotedSkillDir = ConvertTo-ShellLiteral $SkillDir
$quotedContainer = ConvertTo-ShellLiteral $Container
$quotedHostDataDir = ConvertTo-ShellLiteral $HostDataDir
$jobContainerPath = "${Container}:${SkillDir}/job_search_secure.py"
$runtimeEventsContainerPath = "${Container}:${SkillDir}/runtime_events.py"
$detectionsContainerPath = "${Container}:${SkillDir}/detections"
$hostHookPath = "${HostDataDir}/clawguard_post_compile.sh"
$hostCronPath = "${HostDataDir}/staggered_cron.sh"
$hostRuntimeEventsRedactorPath = "${HostDataDir}/clawguard_redact_runtime_events.py"

$remoteScript = @"
set -e
trap "rm -rf $quotedStage" EXIT
echo "Deploying OpenClaw skill package into $SkillDir"
docker cp "$RemoteStage/job_search_secure.py" "$jobContainerPath"
docker cp "$RemoteStage/runtime_events.py" "$runtimeEventsContainerPath"
docker exec $quotedContainer mkdir -p "$SkillDir/detections"
docker cp "$RemoteStage/detections/." "$detectionsContainerPath"
docker exec $quotedContainer mkdir -p "/data/clawguard/runtime_events"
mkdir -p "$HostDataDir/runtime_events_redacted"
docker exec -w $quotedSkillDir $quotedContainer python3 -B -m py_compile job_search_secure.py runtime_events.py detections/asi06_jd_content/detector.py detections/asi01_goal_hijack/detector.py detections/asi02_tool_misuse/detector.py
docker exec -w $quotedSkillDir $quotedContainer python3 -B -c "import job_search_secure as m; import runtime_events as r; print('asi06_module=' + m.ClawGuardASI06JobContentDetector.__module__); print('asi01_module=' + m.ClawGuardASI01GoalHijackDetector.__module__); print('asi02_module=' + m.ClawGuardASI02ToolMisuseDetector.__module__); print('runtime_events_schema=' + r.SCHEMA_VERSION)"
echo "Installing runtime-event redactor on host at $hostRuntimeEventsRedactorPath"
install -m 0755 "$RemoteStage/clawguard_redact_runtime_events.py" "$hostRuntimeEventsRedactorPath"
python3 -B -m py_compile "$hostRuntimeEventsRedactorPath"
grep -q 'REDACTION_STATUS' "$hostRuntimeEventsRedactorPath" && echo "runtime_event_redactor=ok" || (echo "runtime_event_redactor=missing" && exit 1)
echo "Installing post-compile hook on host at $hostHookPath"
mkdir -p $quotedHostDataDir
install -m 0755 "$RemoteStage/clawguard_post_compile.sh" "$hostHookPath"
grep -q 'TELEMETRY_SCHEMA_VERSION' "$hostHookPath" && echo "post_compile_schema_version=ok" || (echo "post_compile_schema_version=missing" && exit 1)
echo "Installing cron wrapper on host at $hostCronPath"
install -m 0755 "$RemoteStage/staggered_cron.sh" "$hostCronPath"
grep -q 'CLAWGUARD_EMAIL_TO' "$hostCronPath" && echo "cron_email_to_forwarding=ok" || (echo "cron_email_to_forwarding=missing" && exit 1)
grep -q 'CLAWGUARD_RUNTIME_EVENTS_ENABLED' "$hostCronPath" && echo "cron_runtime_events_forwarding=ok" || (echo "cron_runtime_events_forwarding=missing" && exit 1)
echo "Deploy complete."
"@

if ($DryRun) {
    Write-Host "Remote: $Remote"
    Write-Host "Container: $Container"
    Write-Host "SkillDir: $SkillDir"
    Write-Host "HostDataDir: $HostDataDir"
    Write-Host "JobScript: $JobScript"
    Write-Host "RuntimeEventsScript: $RuntimeEventsScript"
    Write-Host "RuntimeEventsRedactor: $RuntimeEventsRedactor"
    Write-Host "DetectionsDir: $DetectionsDir"
    Write-Host "PostCompileHook: $PostCompileHook"
    Write-Host "CronScript: $CronScript"
    Write-Host "RemoteStage: $RemoteStage"
    Write-Host "Remote transport: scp temp script, then ssh -o BatchMode=yes $Remote bash /tmp/<script>"
    Write-Host ""
    Write-Host "Remote script:"
    Write-Host $remoteScript
    Write-Host ""
    Write-Host "Dry run complete."
    exit 0
}

Write-Host "Deploying OpenClaw skill package to $Remote..."
Write-Host "  runtime: $JobScript"
Write-Host "  runtime events: $RuntimeEventsScript"
Write-Host "  detections: $DetectionsDir"
Write-Host ""

Invoke-Native "ssh" @("-o", "BatchMode=yes", $Remote, "mkdir -p $quotedStage")
Invoke-Native "scp" @($JobScript, "${Remote}:$RemoteStage/job_search_secure.py")
Invoke-Native "scp" @($RuntimeEventsScript, "${Remote}:$RemoteStage/runtime_events.py")
Invoke-Native "scp" @($RuntimeEventsRedactor, "${Remote}:$RemoteStage/clawguard_redact_runtime_events.py")
Invoke-Native "scp" @("-r", $DetectionsDir, "${Remote}:$RemoteStage/detections")
Invoke-Native "scp" @($PostCompileHook, "${Remote}:$RemoteStage/clawguard_post_compile.sh")
Invoke-Native "scp" @($CronScript, "${Remote}:$RemoteStage/staggered_cron.sh")

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
$localRemoteScript = Join-Path $TempDir "deploy_openclaw_skill_$PID.sh"
$remoteScriptPath = "/tmp/deploy_openclaw_skill_$PID.sh"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $localRemoteScript,
    (($remoteScript -replace "`r`n", "`n") + "`n"),
    $utf8NoBom
)

try {
    Invoke-Native "scp" @($localRemoteScript, "${Remote}:$remoteScriptPath")
    $remoteRunCommand = "bash $remoteScriptPath; rc=`$?; rm -f $remoteScriptPath; exit `$rc"
    Invoke-Native "ssh" @("-o", "BatchMode=yes", $Remote, $remoteRunCommand)
}
finally {
    if (Test-Path -LiteralPath $localRemoteScript) {
        Remove-Item -LiteralPath $localRemoteScript -Force
    }
}

Write-Host ""
Write-Host "OpenClaw skill package deployed and syntax-checked."
