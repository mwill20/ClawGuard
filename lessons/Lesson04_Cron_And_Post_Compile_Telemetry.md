# 🎓 Lesson 04: The Black Box Recorder - Cron and Telemetry Hook

## 🛡️ Welcome Back, Ops Engineer

Goal: understand how the daily VPS schedule runs OpenClaw and exports ClawGuard telemetry.

Time estimate: 45 minutes

Prerequisites:

- Complete Lessons 00-03.
- Understand shell scripts and Docker basics.
- SSH access to `root@31.97.139.139` is optional for local study but required for VPS verification.

Why this matters: detectors only become useful when they run predictably and leave artifacts behind. The cron and post-compile hook are the operational spine.

## 1. Introduction Section

### Learning objectives

- Explain the 9:00-9:30 AM PT daily schedule.
- Describe how `staggered_cron.sh` separates search from compile.
- Explain how `clawguard_post_compile.sh` reads digest and findings data.
- Verify `telemetry_latest.md` on the VPS.
- Identify atomic write behavior.
- Explain why the repo does not auto-push telemetry.

### Plain-English explanation

Cron runs OpenClaw source searches first, then a compile step. If compile succeeds, the post-compile hook writes JSON and Markdown telemetry summaries.

Analogy: this is the black box recorder. Even if nothing suspicious happens, it records the flight summary and proves the system ran.

### Project implements

- Schedule script: `target-agent/skills/job-search-custom/staggered_cron.sh`
- Post-compile hook: `target-agent/skills/job-search-custom/clawguard_post_compile.sh`
- Manual export: `scripts/export_latest_telemetry.ps1`
- Read-only check: `scripts/check_latest_telemetry.ps1`
- Atomic writes: `clawguard_post_compile.sh:33-36`

### Recommended (not implemented here)

- Host-level systemd timers with health notifications.
- Signed telemetry bundles.
- Metrics push to a monitoring backend.
- Alert thresholds for finding count spikes.

## 2. Key Concepts Section

### Terms

| Term | Meaning |
|---|---|
| Staggered cron | Runs each source at a different minute to reduce load and noise. |
| Compile | Scores already-collected jobs and builds a digest. |
| Post-compile hook | Runs only after successful compile to export telemetry. |
| `telemetry_latest.*` | Stable file names for the newest ClawGuard summary. |
| Atomic write | Write temp file, then replace final path with `os.replace()`. |

### Current schedule

```text
9:00 AM PT  -> LinkedIn
9:10 AM PT  -> CyberSecJobs
9:20 AM PT  -> USAJobs
9:30 AM PT  -> Compile digest + post-compile telemetry
```

Project implements:

- Zero-credit maintenance mode.
- Daily source set reduced to LinkedIn, CyberSecJobs, USAJobs.
- `--no-prepare` during compile.
- Post-compile telemetry after successful digest generation.

Recommended (not implemented here):

- Provider-level anomaly detection.
- Cron missed-run detection.
- Automated rollback if detector import fails.

## 3. Code Walkthrough Section

### Cron schedule script

File: `target-agent/skills/job-search-custom/staggered_cron.sh:25`

```bash
CONTAINER="openclaw-utxu-openclaw-1"
SKILL_DIR="/usr/local/lib/node_modules/openclaw/skills/job-search-custom"
ENV_FILE="/docker/openclaw-utxu/.env"
LOG_DIR="/docker/openclaw-utxu/data/clawguard/logs"
POST_COMPILE_HOOK="/docker/openclaw-utxu/data/clawguard/clawguard_post_compile.sh"
```

What it does:

1. Names the Docker container.
2. Sets the skill working directory.
3. Reads secrets from the host `.env`.
4. Writes logs outside the container.
5. Points to the post-compile hook.

### Compile branch

File: `target-agent/skills/job-search-custom/staggered_cron.sh:64`

```bash
if [ "$SITE" = "compile" ]; then
    docker exec \
      -e CLAWGUARD_DATA_DIR="/data/clawguard" \
      -w "$SKILL_DIR" \
      "$CONTAINER" \
      python3 job_search_secure.py digest \
        --compile \
        --format telegram \
        --no-prepare \
      2>&1 | tee "$LOG_DIR/compile_${DATE}.log"
```

Why:

- `--compile` avoids re-searching.
- `--no-prepare` prevents application packages during maintenance mode.
- `tee` preserves logs and terminal output.

### Post-compile atomic write

File: `target-agent/skills/job-search-custom/clawguard_post_compile.sh:33`

```python
def atomic_write(path: Path, content: str):
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(content)
    os.replace(tmp_path, path)
```

What it does:

1. Writes to a process-specific temp file.
2. Replaces the final file atomically.
3. Avoids corrupt partial reads of `telemetry_latest.json` and `.md`.

### Findings query

File: `target-agent/skills/job-search-custom/clawguard_post_compile.sh:63`

```python
if agent_session_id:
    rows = conn.execute(
        """
        SELECT job_id, agent_session_id, rule_id, severity, message, evidence, context, detected_at
        FROM job_security_findings
        WHERE agent_session_id = ?
        ORDER BY detected_at DESC
        """,
        (agent_session_id,),
    ).fetchall()
```

Why: telemetry is causally tied to one digest session. No orphaned findings.

## 4. Hands-On Exercises Section

### 🧪 Exercise 1: Inspect the local cron script

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
Select-String -Path target-agent\skills\job-search-custom\staggered_cron.sh -Pattern "python3 job_search_secure.py|--compile|--no-prepare"
```

Expected output includes:

```text
python3 job_search_secure.py digest \
--compile \
--no-prepare \
```

### 🧪 Exercise 2: Inspect latest VPS telemetry

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
.\scripts\check_latest_telemetry.ps1
```

Expected output begins:

```text
== ClawGuard telemetry_latest.md ==
```

Expected output includes:

```text
Finding count:
Latest job_security_findings rows
Check complete.
```

### 🧪 Exercise 3: Export latest VPS telemetry locally

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
.\scripts\export_latest_telemetry.ps1
```

Expected output begins:

```text
Exported ClawGuard telemetry:
  session:
  finding_count:
  output_dir: lessons\telemetry
```

### 🧪 Exercise 4: Intentional failure scenario

PowerShell:

```powershell
Set-Location C:\Projects\ClawGuard
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_latest_telemetry.ps1 -Remote root@127.0.0.1
```

Expected output includes an SSH connection failure.

Why: this proves the script depends on the configured VPS, not local mock data.

## 5. Interview Preparation Section

**Q: Why run source searches separately from compile?**

**A:** It reduces burst behavior, makes source-level failures easier to isolate, and lets compile work over stored DB state. That is better operational hygiene than a single monolithic run.

**Q: Why does telemetry run after successful compile only?**

**A:** Telemetry should be causally tied to a real digest session. Running after compile avoids orphaned summaries that do not map to an `agent_session_id`.

**Q: Why use atomic writes for `telemetry_latest.json`?**

**A:** Future readers may poll `telemetry_latest`. Atomic replace avoids a brief corrupt-file window during writes.

## 6. Key Takeaways Section

- Cron creates the daily operational rhythm.
- Compile produces the digest session.
- Post-compile telemetry reads findings by `agent_session_id`.
- Atomic writes harden downstream readers.
- Repo telemetry is curated manually; VPS telemetry is continuous.

## 7. Summary Reference Card

| Item | Details |
|---|---|
| Schedule script | `staggered_cron.sh` |
| Hook script | `clawguard_post_compile.sh` |
| VPS telemetry path | `/data/clawguard/telemetry/` |
| Host logs path | `/docker/openclaw-utxu/data/clawguard/logs` |
| Latest summary | `telemetry_latest.md` |
| Export helper | `scripts/export_latest_telemetry.ps1` |
| Check helper | `scripts/check_latest_telemetry.ps1` |

## 8. Next Steps

Study Lesson 05 next: tests and the defense lab. Optional challenge: add a hook field named `detector_runtime_mode` to telemetry JSON after the fallback is removed.

Remember: if production does not leave evidence, it did not happen. 🛡️
