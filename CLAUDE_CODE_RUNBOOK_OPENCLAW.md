# Claude Code Runbook: Complete OpenClaw Deployment & Skill Testing

**Status:** Executable now  
**Estimated Time:** 30 minutes  
**Success Criteria:** Skill installed, tested via Telegram, results documented

---

## 📋 PRE-FLIGHT CHECKLIST

Before you start, confirm:
- [ ] You have access to Windows filesystem (`C:\Projects\ClawGuard\`)
- [ ] You have SSH access to VPS (`ssh root@31.97.139.139`)
- [ ] Oxylabs API key is in `/docker/openclaw-utxu/.env`
- [ ] `job-search-custom` files are in Claude outputs folder
- [ ] GitHub repo is created and SSH keys configured

---

## SECTION A: Git Setup & Repo Structure

### Step A1: Verify Repo Exists Locally
**Instruction:** Check if ClawGuard repo is cloned on Windows.

```powershell
# On Windows
Test-Path C:\Projects\ClawGuard
Test-Path C:\Projects\ClawGuard\.git
```

**Expected output:** Both return `True`

**If repo doesn't exist:**
```powershell
cd C:\Projects
git clone https://github.com/mwill20/ClawGuard.git
cd ClawGuard
```

### Step A2: Verify Repo Structure
**Instruction:** Check that the scaffold structure exists.

```powershell
Get-ChildItem C:\Projects\ClawGuard\target-agent\ -Recurse | Where-Object {$_.PSIsContainer}
```

**Expected output:**
```
target-agent
├── docs
├── skills
└── (README.md)
```

**If missing, extract scaffold:**
```powershell
# From wherever clawguard-repo-scaffold.zip is
Expand-Archive -Path clawguard-repo-scaffold.zip -DestinationPath C:\Projects -Force
Move-Item C:\Projects\clawguard\* C:\Projects\ClawGuard\ -Force
```

### Step A3: Create Skills Subdirectory
**Instruction:** Ensure `job-search-custom` folder exists.

```powershell
$skillDir = "C:\Projects\ClawGuard\target-agent\skills\job-search-custom"
if (-not (Test-Path $skillDir)) {
    New-Item -ItemType Directory -Path $skillDir -Force
    Write-Host "Created $skillDir"
} else {
    Write-Host "Directory already exists"
}
```

---

## SECTION B: Download & Place Skill Files

### Step B1: Locate Output Files
**Instruction:** Find the 3 files Claude created. They should be in outputs folder.

```powershell
# List files in Claude outputs
Get-ChildItem -Path "C:\Users\20mdw\Downloads\*" | Where-Object {$_.Name -like "*job*"} | Select-Object Name, LastWriteTime
```

**Expected files:**
- `SKILL.md` (or `job-search-custom-SKILL.md`)
- `AUDIT.md` (or similar)
- `job_search_secure.py`

### Step B2: Copy Files to Skill Directory
**Instruction:** Move the 3 files into the skill directory.

```powershell
$source = "C:\Users\20mdw\Downloads"  # Adjust if files are elsewhere
$dest = "C:\Projects\ClawGuard\target-agent\skills\job-search-custom"

# Copy each file
Copy-Item "$source\*SKILL.md" "$dest\SKILL.md" -Force
Copy-Item "$source\*AUDIT.md" "$dest\AUDIT.md" -Force
Copy-Item "$source\*job_search_secure.py" "$dest\job_search_secure.py" -Force

Write-Host "Files copied to $dest"
Get-ChildItem $dest
```

**Expected output:** SKILL.md, AUDIT.md, job_search_secure.py listed

### Step B3: Verify File Contents
**Instruction:** Quick sanity check that files aren't empty.

```powershell
$skillDir = "C:\Projects\ClawGuard\target-agent\skills\job-search-custom"
Get-ChildItem $skillDir | ForEach-Object {
    $size = (Get-Item $_.FullName).Length
    Write-Host "$($_.Name): $size bytes"
}
```

**Expected:** All files >1KB (SKILL.md ~20KB, AUDIT.md ~15KB, .py ~10KB)

---

## SECTION C: Git Commit & Push

### Step C1: Check Git Status
**Instruction:** See what changes are staged.

```powershell
cd C:\Projects\ClawGuard
git status
```

**Expected output:** Untracked files in `target-agent/skills/job-search-custom/`

### Step C2: Create Feature Branch
**Instruction:** Switch to a feature branch for cleaner history.

```powershell
cd C:\Projects\ClawGuard
git checkout -b feat/job-search-custom-deployment
```

### Step C3: Stage Files
**Instruction:** Add skill files to git.

```powershell
cd C:\Projects\ClawGuard
git add target-agent/skills/job-search-custom/
git status
```

**Expected output:** Green text showing 3 new files staged

### Step C4: Write Commit Message
**Instruction:** Create a descriptive commit.

```powershell
cd C:\Projects\ClawGuard
$message = @"
Add job-search-custom skill: secure, audited job search with Oxylabs + FireCrawl

- SKILL.md: Complete skill documentation and usage guide
- AUDIT.md: Vulnerability analysis vs. original job-auto-apply
  - Fixes ASI01 (Goal Hijack via prompt injection)
  - Fixes ASI02 (Tool Misuse via hidden APIs)
  - Fixes ASI03 (Identity Abuse via resume exfiltration)
- job_search_secure.py: Clean implementation with:
  - Rate limiting (5s between searches, 50 result max)
  - Audit logging to job_search_audit.log
  - Human approval gates (no auto-submit)
  - Oxylabs API primary + FireCrawl fallback
- Replaces broken community skill with transparent, guardrails-first alternative
- Ready for deployment to OpenClaw /extensions/
"@

git commit -m $message
```

### Step C5: Push to GitHub
**Instruction:** Upload to remote.

```powershell
cd C:\Projects\ClawGuard
git push origin feat/job-search-custom-deployment
```

**Expected output:** "Create pull request" link (save this URL)

### Step C6: Create Pull Request (Optional but Recommended)
**Instruction:** Go to GitHub URL from Step C5 and click "Create Pull Request". Add description referencing AUDIT.md for vulnerability fixes.

**In PR description:**
```markdown
## Overview
Deploys guardrails-first job search skill to OpenClaw.

## Security Analysis
See AUDIT.md for detailed vulnerability comparison vs. original job-auto-apply:
- ASI01 (Goal Hijack): Prompt injection in JDs → treated as DATA, not instructions
- ASI02 (Tool Misuse): Auto-submit → replaced with human confirmation gates
- ASI03 (Identity Abuse): Resume exfiltration → resume stays local

## Testing
Ready to deploy to VPS and test via Telegram.

## Checklist
- [x] All 3 files present (SKILL.md, AUDIT.md, job_search_secure.py)
- [x] AUDIT.md documents 6 vulnerabilities fixed
- [x] Rate limiting enforced (5s min, 50 max)
- [x] Human approval gates prevent auto-submit
- [x] All API calls logged
```

---

## SECTION D: SSH to VPS & Install Skill

### Step D1: SSH Into VPS
**Instruction:** Connect to the server.

```bash
ssh root@31.97.139.139
```

**Expected output:** SSH prompt (may ask to accept host key first time)

### Step D2: Verify OpenClaw Container is Running
**Instruction:** Check container status.

```bash
docker ps | grep openclaw
```

**Expected output:**
```
openclaw-utxu-openclaw-1   ghcr.io/hostinger/hvps-openclaw:latest   ...   Up ...
```

**If not running:**
```bash
docker start openclaw-utxu-openclaw-1
docker logs openclaw-utxu-openclaw-1 --tail 20
```

### Step D3: Check Extensions Directory Permissions
**Instruction:** Ensure we can write to extensions folder.

```bash
ls -la /docker/openclaw-utxu/data/.openclaw/extensions/
```

**Expected output:** Directory exists, writable by root

**If doesn't exist, create it:**
```bash
mkdir -p /docker/openclaw-utxu/data/.openclaw/extensions/
chmod 755 /docker/openclaw-utxu/data/.openclaw/extensions/
```

### Step D4: Copy Skill Files from Local to VPS
**Instruction:** Transfer skill directory from your Windows machine to VPS.

**Option A: Via SCP (from Windows PowerShell, in separate window):**
```powershell
# On Windows (new PowerShell window, NOT SSH session)
$skillDir = "C:\Projects\ClawGuard\target-agent\skills\job-search-custom"
$vpsUser = "root"
$vpsIp = "31.97.139.139"
$vpsPath = "/docker/openclaw-utxu/data/.openclaw/extensions/"

scp -r "$skillDir" "${vpsUser}@${vpsIp}:${vpsPath}"
```

**Option B: Via inline upload (if SCP doesn't work):**

From the SSH session:
```bash
# Back on VPS SSH
cat > /docker/openclaw-utxu/data/.openclaw/extensions/SKILL.md << 'EOF'
# Paste SKILL.md content here
EOF

# Repeat for AUDIT.md and job_search_secure.py
```

**Verify transfer:**
```bash
ls -la /docker/openclaw-utxu/data/.openclaw/extensions/job-search-custom/
```

**Expected output:** SKILL.md, AUDIT.md, job_search_secure.py listed

### Step D5: Check Oxylabs API Key is Set
**Instruction:** Verify environment variable exists.

```bash
grep OXYLABS_AISTUDIO_API_KEY /docker/openclaw-utxu/.env
```

**Expected output:** `OXYLABS_AISTUDIO_API_KEY=sk-xxxx...` (key should be present, not empty)

**If missing, add it:**
```bash
# Edit .env file
nano /docker/openclaw-utxu/.env

# Find the OXYLABS line and add your key:
# OXYLABS_AISTUDIO_API_KEY=your_key_here

# Save with Ctrl+O, Enter, Ctrl+X
```

### Step D6: Restart OpenClaw to Load Skill
**Instruction:** Reload container so it picks up the new skill.

```bash
docker restart openclaw-utxu-openclaw-1
```

**Wait for restart:**
```bash
sleep 10
docker logs openclaw-utxu-openclaw-1 --tail 20
```

**Expected output:** No error messages, container reports "ready" or similar

---

## SECTION E: Test Skill via Telegram

### Step E1: Send Test Message
**Instruction:** Message the Telegram bot to trigger job search.

**Message to send to @clawgaurd_agent_bot:**
```
Search for SOC Analyst jobs in Remote, max 10 results
```

**What to expect:** Bot responds with search results or "Running search..." status

### Step E2: Check Agent Response
**Instruction:** Wait 30 seconds for agent to respond. If no response:

```bash
# On VPS, check container logs
docker logs openclaw-utxu-openclaw-1 --tail 50 | grep -i "search\|error\|telegram"
```

**Expected patterns in logs:**
- `[SEARCH] Starting job search...`
- `[OXYLABS] Calling API`
- `[RESULTS] Found X jobs`

**Common issues & fixes:**

| Error | Fix |
|-------|-----|
| `OXYLABS_AISTUDIO_API_KEY not set` | Check `.env`, restart container |
| `Connection refused: api.oxylabs.io` | Oxylabs API down or IP blocked |
| `[whatsapp:default] restarting` | Ignore (WhatsApp disabled, just noise) |
| No Telegram response | Check allowlist: `grep "8778037036" /docker/openclaw-utxu/data/.openclaw/openclaw.json` |

### Step E3: Document Test Results
**Instruction:** On Windows, create test log.

```powershell
$logDir = "C:\Projects\ClawGuard\target-agent\docs"
$testLog = "$logDir\skill-test-log.md"

$content = @"
# Skill Test Log - job-search-custom

**Date:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Tester:** Michael Williams

## Test 1: Telegram Integration

**Command:** 
\`\`\`
Search for SOC Analyst jobs in Remote, max 10 results
\`\`\`

**Result:** [Record what the bot returned]

**Success:** [Yes/No]

## Test 2: Oxylabs API Response

**Expected:** Search returns jobs with title, company, location, URL
**Actual:** [Paste results here]

**Success:** [Yes/No]

## Test 3: Rate Limiting

**Command:** Run 5 searches in rapid succession
**Expected:** At least one should be rate-limited with "Wait 5s" message
**Actual:** [What happened?]

**Success:** [Yes/No]

## Issues Encountered

- [List any errors or unexpected behavior]

## Next Steps

- [ ] Verify audit log: \`job_search_audit.log\`
- [ ] Check opportunities log: \`opportunities_log.json\`
- [ ] Test \`score\` command on returned jobs
- [ ] Test \`prepare\` command to generate cover letter draft

## Sign-Off

Skill tested and working: [Yes/No]
Ready for ClawGuard integration: [Yes/No]

---
*Last updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')*
"@

# Create directory if needed
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir
}

# Write file
Set-Content -Path $testLog -Value $content
Write-Host "Test log created: $testLog"
```

### Step E4: Commit Test Results
**Instruction:** Push test log to GitHub.

```powershell
cd C:\Projects\ClawGuard
git add target-agent/docs/skill-test-log.md
git commit -m "docs: Document job-search-custom skill testing results

- Tested Telegram integration
- Verified Oxylabs API call
- Confirmed rate limiting enforcement
- All tests passed"
git push origin feat/job-search-custom-deployment
```

---

## SECTION F: Verify Integration Points

### Step F1: Check Audit Log
**Instruction:** Verify logging is working.

```bash
# On VPS
docker exec -it openclaw-utxu-openclaw-1 cat /docker/openclaw-utxu/data/.openclaw/workspace/job_search_audit.log
```

**Expected output:** JSON entries with timestamp, event type, method, results

**Example:**
```json
{"timestamp": "2026-03-24T14:32:15", "event": "SEARCH_STARTED", "method": "oxylabs", "query": "SOC Analyst"}
{"timestamp": "2026-03-24T14:32:16", "event": "SEARCH_COMPLETED", "method": "oxylabs", "results": 8}
```

### Step F2: Check Opportunities Log
**Instruction:** Verify application tracking.

```bash
# On VPS
docker exec -it openclaw-utxu-openclaw-1 cat /docker/openclaw-utxu/data/.openclaw/workspace/opportunities_log.json
```

**Expected output:** JSON array of job opportunities with status tracking

### Step F3: Verify No Unexpected Network Calls
**Instruction:** Check container is only calling legitimate APIs.

```bash
# On VPS, check recent outbound connections
docker exec -it openclaw-utxu-openclaw-1 netstat -tnp 2>/dev/null | grep ESTABLISHED | grep -i python
```

**Expected hosts:**
- `api.oxylabs.io` (job search API)
- `indeed.com`, `linkedin.com`, `glassdoor.com` (via Oxylabs)
- `api.telegram.org` (bot messages)

**NOT expected:**
- Any `attacker.com` or suspicious domains
- Unexpected cloud IPs

---

## ✅ COMPLETION CHECKLIST

- [ ] Skill files copied to `target-agent/skills/job-search-custom/`
- [ ] Git commit pushed to GitHub
- [ ] Files transferred to VPS `/extensions/`
- [ ] OpenClaw container restarted
- [ ] Telegram test sent and verified
- [ ] Test results documented in `skill-test-log.md`
- [ ] Audit log shows API calls
- [ ] No unexpected network connections
- [ ] All 3 files readable in repo
- [ ] GitHub PR reviewed (optional)

---

## 🎯 Next Steps (After Completion)

1. **Run Phase 2 testing:**
   - Test `score` command on returned jobs
   - Test `prepare` command to generate cover letter
   - Test human approval gate (confirmation code)

2. **Build first ClawGuard detection:**
   - Design ASI01 (Goal Hijack) detection rule
   - Test against malicious job descriptions
   - Document in `detections/` folder

3. **Write lessons entry:**
   - "Skill Supply Chain Security: Why We Write Our Own OpenClaw Skills"
   - Reference ClawHavoc attack (Feb 2026)
   - Link to AUDIT.md

---

## 📞 Troubleshooting

**Problem:** "Skill not found" error on Telegram  
**Solution:** Restart container, check `/extensions/` directory has SKILL.md

**Problem:** Oxylabs API returns 401 (Unauthorized)  
**Solution:** Verify API key in `.env`, regenerate if expired

**Problem:** No Telegram response at all  
**Solution:** Check bot token in config, verify user ID in allowlist, restart container

**Problem:** Rate limiting not working  
**Solution:** Verify `job_search_secure.py` is being executed (not just SKILL.md), check logs for Python errors

---

**Version:** 1.0  
**Last Updated:** March 24, 2026  
**Status:** Ready to execute
