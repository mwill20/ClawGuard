#!/bin/bash
# ============================================================================
# ClawGuard Post-Compile Telemetry Hook
#
# Runs after a successful OpenClaw digest compile. Produces a zero-UI telemetry
# summary for ClawGuard review without sending alerts for clean runs.
# ============================================================================

set -euo pipefail

CONTAINER="${OPENCLAW_CONTAINER:-openclaw-utxu-openclaw-1}"
LOG_DIR="/docker/openclaw-utxu/data/clawguard/logs"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

mkdir -p "$LOG_DIR"

echo "[$TIMESTAMP] ClawGuard post-compile telemetry started" | tee -a "$LOG_DIR/cron.log"

set +e
docker exec -i \
  -e CLAWGUARD_DATA_DIR="/data/clawguard" \
  "$CONTAINER" \
  python3 - <<'PY' 2>&1 | tee "$LOG_DIR/clawguard_post_compile_${DATE}.log"
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path


data_dir = Path(os.getenv("CLAWGUARD_DATA_DIR", "/data/clawguard"))
digests_dir = data_dir / "digests"
telemetry_dir = data_dir / "telemetry"
db_path = data_dir / "jobs.db"

telemetry_dir.mkdir(parents=True, exist_ok=True)

today = datetime.now().strftime("%Y-%m-%d")
today_digest = digests_dir / f"digest_{today}.json"
if today_digest.exists():
    digest_path = today_digest
else:
    candidates = sorted(digests_dir.glob("digest_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No digest archive found; post-compile telemetry cannot run.")
    digest_path = candidates[0]

digest = json.loads(digest_path.read_text())
digest_date = digest.get("date") or today
agent_session_id = digest.get("agent_session_id")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

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
else:
    rows = []

findings = []
for row in rows:
    evidence = json.loads(row["evidence"] or "{}")
    context = json.loads(row["context"] or "{}")
    findings.append({
        "job_id": row["job_id"],
        "agent_session_id": row["agent_session_id"],
        "rule_id": row["rule_id"],
        "severity": row["severity"],
        "message": row["message"],
        "evidence": evidence,
        "context": context,
        "detected_at": row["detected_at"],
    })

rule_counts = Counter(f["rule_id"] for f in findings)
severity_counts = Counter(f["severity"] for f in findings)
source_counts = Counter(f["context"].get("source_platform", "unknown") for f in findings)
top_match_source_counts = Counter(
    match.get("source", "unknown") for match in digest.get("top_matches", [])
)

summary = {
    "generated_at": datetime.now().isoformat(),
    "digest_path": str(digest_path),
    "agent_session_id": agent_session_id,
    "finding_count": len(findings),
    "rule_counts": dict(sorted(rule_counts.items())),
    "severity_counts": dict(sorted(severity_counts.items())),
    "finding_source_platform_counts": dict(sorted(source_counts.items())),
    "digest_top_match_source_counts": dict(sorted(top_match_source_counts.items())),
    "digest_summary": digest.get("summary", {}),
    "findings": findings,
}

safe_session = agent_session_id or "no-session"
json_path = telemetry_dir / f"telemetry_{digest_date}_{safe_session}.json"
md_path = telemetry_dir / f"telemetry_{digest_date}_{safe_session}.md"

json_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
(telemetry_dir / "telemetry_latest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

md_lines = [
    f"# ClawGuard Telemetry Summary - {digest_date}",
    "",
    f"- Generated at: `{summary['generated_at']}`",
    f"- Digest archive: `{digest_path.name}`",
    f"- Agent session: `{agent_session_id}`",
    f"- Finding count: `{len(findings)}`",
    f"- Digest total found: `{digest.get('summary', {}).get('total_found', 0)}`",
    f"- Digest new jobs: `{digest.get('summary', {}).get('new_jobs', 0)}`",
    f"- Auto-prepared: `{digest.get('summary', {}).get('auto_prepared', 0)}`",
    f"- Credits used today: `{digest.get('summary', {}).get('credits_used_today', 0)}`",
    "",
    "## Finding Breakdown",
    "",
    f"- Rules: `{dict(sorted(rule_counts.items()))}`",
    f"- Severities: `{dict(sorted(severity_counts.items()))}`",
    f"- Finding sources: `{dict(sorted(source_counts.items()))}`",
    f"- Top-match sources: `{dict(sorted(top_match_source_counts.items()))}`",
    "",
]

if findings:
    md_lines.extend(["## Findings", ""])
    for finding in findings:
        context = finding["context"]
        md_lines.extend([
            f"### {finding['rule_id']} - {finding['severity']}",
            "",
            f"- Job: `{context.get('job_title', finding['job_id'])}`",
            f"- Source: `{context.get('source_platform', 'unknown')}`",
            f"- Source field: `{context.get('source_field', 'unknown')}`",
            f"- Detected at: `{finding['detected_at']}`",
            f"- Message: {finding['message']}",
            "",
        ])
else:
    md_lines.extend([
        "## Findings",
        "",
        "No ASI06 findings were recorded for this session. This is a clean-content baseline signal.",
        "",
    ])

md_path.write_text("\n".join(md_lines))
(telemetry_dir / "telemetry_latest.md").write_text("\n".join(md_lines))

print(json.dumps({
    "agent_session_id": agent_session_id,
    "finding_count": len(findings),
    "json_path": str(json_path),
    "markdown_path": str(md_path),
}, sort_keys=True))
PY
HOOK_EXIT=${PIPESTATUS[0]}
set -e

if [ "$HOOK_EXIT" -ne 0 ]; then
    echo "[$TIMESTAMP] ClawGuard post-compile telemetry failed (exit=$HOOK_EXIT)" | tee -a "$LOG_DIR/cron.log"
else
    echo "[$TIMESTAMP] ClawGuard post-compile telemetry completed" | tee -a "$LOG_DIR/cron.log"
fi

exit "$HOOK_EXIT"
