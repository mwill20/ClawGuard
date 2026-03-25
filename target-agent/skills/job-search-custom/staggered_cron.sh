#!/bin/bash
# ============================================================================
# ClawGuard Staggered Job Search Pipeline — Cron Script
#
# Called by cron with a single argument: site key or "compile"
# Each site runs at a different time (30-min intervals, 9am-12:30pm Pacific)
# Final "compile" at 1pm assembles digest, auto-prepares materials, notifies
#
# Cron schedule (add to VPS host crontab):
#   0  16 * * 1-5  .../staggered_cron.sh linkedin
#   30 16 * * 1-5  .../staggered_cron.sh cybersecjobs
#   0  17 * * 1-5  .../staggered_cron.sh infosecjobs
#   30 17 * * 1-5  .../staggered_cron.sh indeed
#   0  18 * * 1-5  .../staggered_cron.sh dice
#   30 18 * * 1-5  .../staggered_cron.sh monster
#   0  19 * * 1-5  .../staggered_cron.sh simplyhired
#   30 19 * * 1-5  .../staggered_cron.sh usajobs
#   0  19 * * 1-5  .../staggered_cron.sh remotehunter  # shares 12pm slot
#   0  20 * * 1-5  .../staggered_cron.sh compile
# ============================================================================

set -euo pipefail

SITE="${1:-}"
if [ -z "$SITE" ]; then
    echo "Usage: $0 <site_key|compile>"
    exit 1
fi

CONTAINER="openclaw-utxu-openclaw-1"
SKILL_DIR="/usr/local/lib/node_modules/openclaw/skills/job-search-custom"
ENV_FILE="/docker/openclaw-utxu/.env"
LOG_DIR="/docker/openclaw-utxu/data/clawguard/logs"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

mkdir -p "$LOG_DIR"

# Extract env vars from .env file
get_env() {
    grep "^$1=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo ""
}

API_KEY=$(get_env "OXYLABS_AISTUDIO_API_KEY")
EMAIL_FROM=$(get_env "CLAWGUARD_EMAIL_FROM")
EMAIL_PASS=$(get_env "CLAWGUARD_EMAIL_PASSWORD")

# Ensure pip package is installed (idempotent, survives container restarts)
docker exec "$CONTAINER" pip install oxylabs-ai-studio --break-system-packages -q 2>/dev/null || true

echo "[$TIMESTAMP] Running: $SITE" | tee -a "$LOG_DIR/cron.log"

if [ "$SITE" = "compile" ]; then
    # Final compilation: score, auto-prepare STRONG+GOOD, notify via Telegram + email
    docker exec \
      -e OXYLABS_AISTUDIO_API_KEY="$API_KEY" \
      -e CLAWGUARD_EMAIL_FROM="$EMAIL_FROM" \
      -e CLAWGUARD_EMAIL_PASSWORD="$EMAIL_PASS" \
      -e CLAWGUARD_DATA_DIR="/data/clawguard" \
      -w "$SKILL_DIR" \
      "$CONTAINER" \
      python3 job_search_secure.py digest \
        --compile \
        --format telegram \
      2>&1 | tee "$LOG_DIR/compile_${DATE}.log"
else
    # Search single site, store to DB
    docker exec \
      -e OXYLABS_AISTUDIO_API_KEY="$API_KEY" \
      -e CLAWGUARD_DATA_DIR="/data/clawguard" \
      -w "$SKILL_DIR" \
      "$CONTAINER" \
      python3 job_search_secure.py digest \
        --site "$SITE" \
        --budget 6 \
        --no-notify \
      2>&1 | tee "$LOG_DIR/search_${SITE}_${DATE}.log"
fi

EXIT_CODE=${PIPESTATUS[0]}
echo "[$TIMESTAMP] $SITE completed (exit=$EXIT_CODE)" | tee -a "$LOG_DIR/cron.log"
