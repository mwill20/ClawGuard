#!/bin/bash
# ============================================================================
# ClawGuard Daily Job Search Digest — Cron Script
# Schedule: 9:00 AM Pacific, Mon-Fri
# Cron entry: 0 16 * * 1-5 /docker/openclaw-utxu/data/.openclaw/extensions/job-search-custom/daily_digest_cron.sh
# (16:00 UTC = 9:00 AM Pacific)
#
# This script:
# 1. Runs the job search digest inside the OpenClaw Docker container
# 2. Searches all enabled job sites with budget cap
# 3. Scores results against resume/profile
# 4. Outputs Telegram-formatted digest
# 5. Logs results for audit trail
# ============================================================================

set -euo pipefail

CONTAINER_NAME="openclaw-utxu"
SKILL_DIR="/usr/local/lib/node_modules/openclaw/skills/job-search-custom"
LOG_DIR="/docker/openclaw-utxu/data/.openclaw/extensions/job-search-custom/logs"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

# Create log directory if needed
mkdir -p "$LOG_DIR"

echo "[$TIMESTAMP] Starting daily job search digest..." | tee -a "$LOG_DIR/cron.log"

# Ensure pip package is installed (survives container restarts)
docker exec "$CONTAINER_NAME" pip install oxylabs-ai-studio --break-system-packages -q 2>/dev/null || true

# Run the digest with budget cap of 50 credits
# Output both JSON (for archival) and Telegram (for notification)
docker exec \
  -e OXYLABS_AISTUDIO_API_KEY="$(grep '^OXYLABS_AISTUDIO_API_KEY=' /docker/openclaw-utxu/.env | cut -d= -f2)" \
  -w "$SKILL_DIR" \
  "$CONTAINER_NAME" \
  python3 job_search_secure.py digest \
    --budget 50 \
    --min-score 0.40 \
    --format telegram \
  2>&1 | tee "$LOG_DIR/digest_${DATE}.log"

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$TIMESTAMP] Digest completed successfully" | tee -a "$LOG_DIR/cron.log"
else
    echo "[$TIMESTAMP] Digest failed with exit code $EXIT_CODE" | tee -a "$LOG_DIR/cron.log"
fi

# Also save the JSON version for archival
docker exec \
  -e OXYLABS_AISTUDIO_API_KEY="$(grep '^OXYLABS_AISTUDIO_API_KEY=' /docker/openclaw-utxu/.env | cut -d= -f2)" \
  -w "$SKILL_DIR" \
  "$CONTAINER_NAME" \
  python3 job_search_secure.py digest \
    --budget 0 \
    --format json \
  > "$LOG_DIR/digest_${DATE}.json" 2>/dev/null || true

echo "[$TIMESTAMP] Done. Logs: $LOG_DIR/digest_${DATE}.log" | tee -a "$LOG_DIR/cron.log"
