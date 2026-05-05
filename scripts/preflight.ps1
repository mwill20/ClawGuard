param(
    [switch]$RequireClean
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "== $Name =="
    & $Command
    Write-Host "PASS: $Name"
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $output | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            Write-Host $_.Exception.Message
        }
        else {
            Write-Host $_.ToString()
        }
    }
    if ($exitCode -ne 0) {
        throw "$FilePath failed with exit code $exitCode"
    }
}

function Assert-GitGrepNoMatch {
    param(
        [string]$Name,
        [string]$Pattern
    )

    Write-Host ""
    Write-Host "== $Name =="
    & git grep -I -n -E --untracked $Pattern -- . ":(exclude)scripts/preflight.ps1"
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        throw "$Name found forbidden or stale tracked text"
    }
    if ($exitCode -ne 1) {
        throw "$Name scan failed with exit code $exitCode"
    }
    Write-Host "PASS: $Name"
}

Invoke-Step "Unit tests" {
    Invoke-Native "python" @("-B", "-m", "unittest", "discover", "-s", "tests")
}

Invoke-Step "ASI06 synthetic fixture evaluation" {
    Invoke-Native "python" @(
        "-B",
        "scripts\evaluate_asi06.py",
        "--input",
        "examples\asi06_labeled_eval.json",
        "--expected-micro-f1",
        "1.0",
        "--hide-timing"
    )
}

Invoke-Step "ASI02 synthetic fixture evaluation" {
    Invoke-Native "python" @(
        "-B",
        "scripts\evaluate_asi02.py",
        "--input",
        "examples\asi02_labeled_eval.json",
        "--expected-micro-f1",
        "1.0",
        "--hide-timing"
    )
}

Invoke-Step "Telemetry sample validation" {
    Invoke-Native "python" @(
        "-B",
        "scripts\validate_telemetry.py",
        "--input",
        "examples\telemetry_sample.json"
    )
}

Invoke-Step "Sample detector output matches expected JSON" {
    $code = @'
import json
from pathlib import Path
from detections.asi06_jd_content.detector import detect_job_content

jobs = json.loads(Path('examples/sample_input.json').read_text(encoding='utf-8'))
actual = [
    {'job_id': job['job_id'], 'rule_ids': [finding.rule_id for finding in detect_job_content(job)]}
    for job in jobs
]
expected = json.loads(Path('examples/sample_output.json').read_text(encoding='utf-8'))
if actual != expected:
    raise SystemExit('sample output mismatch')
print('sample output ok')
'@
    Invoke-Native "python" @("-B", "-c", $code)
}

Invoke-Step "Python syntax parse" {
    $code = @'
import ast
from pathlib import Path

paths = [
    'scripts/evaluate_asi06.py',
    'scripts/evaluate_asi02.py',
    'scripts/export_telemetry.py',
    'scripts/select_review_sessions.py',
    'scripts/telemetry_redaction.py',
    'scripts/validate_telemetry.py',
    'detections/asi02_tool_misuse/detector.py',
    'target-agent/skills/job-search-custom/job_search_secure.py',
]
for path in paths:
    ast.parse(Path(path).read_text(encoding='utf-8'), filename=path)
print('syntax ok')
'@
    Invoke-Native "python" @("-B", "-c", $code)
}

Invoke-Step "OpenClaw deploy helper dry run" {
    Invoke-Native "powershell" @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "scripts\deploy_openclaw_skill.ps1",
        "-DryRun"
    )
}

Invoke-Step "Telemetry export helper dry run" {
    Invoke-Native "python" @(
        "-B",
        "scripts\export_telemetry.py",
        "--input-dir",
        "examples",
        "--output-dir",
        "C:\tmp\clawguard-export-dryrun",
        "--session",
        "digest-20260503T163003-b91b67e1",
        "--dry-run"
    )
    Invoke-Native "powershell" @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "scripts\export_telemetry.ps1",
        "-DryRun",
        "-Sessions",
        "digest-20260503T163003-b91b67e1"
    )
}

Assert-GitGrepNoMatch `
    -Name "No copied external repo-standard source files" `
    -Pattern "REPO_STANDARDS_AGENT|repo standards are a must"

Assert-GitGrepNoMatch `
    -Name "No tracked private job-search profile strings" `
    -Pattern "mwill\.itmission|206\.474\.0889|11:11 Systems|University of Texas at Austin|Western Governors University|Cybersecurity Analyst II \| 11:11|PurpleLens|SANS Technology Institute|ProtectAI|Hugging Face|Modern Security|Practical DevSecOps|Cyber Defense & Intelligence Center|CDIC"

Assert-GitGrepNoMatch `
    -Name "No stale test-count claims" `
    -Pattern "35 tests|35/35|Ran 35|28 tests|28/28|Ran 28|24 tests|24/24|Ran 24|14 tests|14/14|Ran 14|12 tests|12/12|Ran 12|11 tests|11/11|Ran 11"

Invoke-Step "Git diff whitespace check" {
    Invoke-Native "git" @("diff", "--check")
}

if ($RequireClean) {
    Invoke-Step "Git worktree clean check" {
        $status = & git status --porcelain
        if ($status) {
            $status | ForEach-Object { Write-Host $_ }
            throw "Working tree is not clean"
        }
        Write-Host "working tree clean"
    }
}

Write-Host ""
Write-Host "Preflight passed."
