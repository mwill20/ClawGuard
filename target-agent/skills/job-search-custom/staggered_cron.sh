#!/bin/bash
# ============================================================================
# ClawGuard Maintenance Job Search Pipeline - Cron Script
#
# Called by cron with a single argument: site key or "compile".
# Low-volume mode while active interview/offer loops are in progress.
# Runs the minimal source set daily, staggered within the 9 AM PT hour, and
# compiles without auto-preparing new application packages or enriching JDs.
#
# Cron schedule (add to VPS host crontab):
#   0  16 * * *  .../staggered_cron.sh linkedin
#   10 16 * * *  .../staggered_cron.sh cybersecjobs
#   20 16 * * *  .../staggered_cron.sh usajobs
#   30 16 * * *  .../staggered_cron.sh compile
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
POST_COMPILE_HOOK="/docker/openclaw-utxu/data/clawguard/clawguard_post_compile.sh"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)

mkdir -p "$LOG_DIR"

# Extract env vars from .env file
get_env() {
    grep "^$1=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo ""
}

API_KEY=$(get_env "OXYLABS_AISTUDIO_API_KEY")
BRAVE_API_KEY=$(get_env "BRAVE_SEARCH_API_KEY")
USAJOBS_KEY=$(get_env "USAJOBS_AUTH_KEY")
USAJOBS_AGENT=$(get_env "USAJOBS_USER_AGENT")
SEARCH_PROVIDER=$(get_env "CLAWGUARD_SEARCH_PROVIDER")
DISABLE_OXYLABS=$(get_env "CLAWGUARD_DISABLE_OXYLABS")
FALLBACK_ON_EMPTY=$(get_env "CLAWGUARD_FALLBACK_ON_EMPTY")
AUTO_PREPARE_THRESHOLD=$(get_env "CLAWGUARD_AUTO_PREPARE_THRESHOLD")
ENRICHMENT_DAILY_CAP=$(get_env "CLAWGUARD_ENRICHMENT_DAILY_CAP")
DIGEST_MAX_RESULTS_PER_SITE=$(get_env "CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE")
TOP_MATCH_LIMIT=$(get_env "CLAWGUARD_DIGEST_TOP_MATCH_LIMIT")
EMAIL_FROM=$(get_env "CLAWGUARD_EMAIL_FROM")
EMAIL_PASS=$(get_env "CLAWGUARD_EMAIL_PASSWORD")

AUTO_PREPARE_THRESHOLD="${AUTO_PREPARE_THRESHOLD:-0.75}"
ENRICHMENT_DAILY_CAP="${ENRICHMENT_DAILY_CAP:-0}"
DIGEST_MAX_RESULTS_PER_SITE="${DIGEST_MAX_RESULTS_PER_SITE:-5}"
TOP_MATCH_LIMIT="${TOP_MATCH_LIMIT:-10}"

# Ensure pip package is installed (idempotent, survives container restarts)
docker exec "$CONTAINER" pip install oxylabs-ai-studio --break-system-packages -q 2>/dev/null || true

echo "[$TIMESTAMP] Running: $SITE" | tee -a "$LOG_DIR/cron.log"

if [ "$SITE" = "compile" ]; then
    # Maintenance compilation: score + notify, no new application packages.
    set +e
    docker exec \
      -e OXYLABS_AISTUDIO_API_KEY="$API_KEY" \
      -e BRAVE_SEARCH_API_KEY="$BRAVE_API_KEY" \
      -e USAJOBS_AUTH_KEY="$USAJOBS_KEY" \
      -e USAJOBS_USER_AGENT="$USAJOBS_AGENT" \
      -e CLAWGUARD_SEARCH_PROVIDER="$SEARCH_PROVIDER" \
      -e CLAWGUARD_DISABLE_OXYLABS="$DISABLE_OXYLABS" \
      -e CLAWGUARD_FALLBACK_ON_EMPTY="$FALLBACK_ON_EMPTY" \
      -e CLAWGUARD_AUTO_PREPARE_THRESHOLD="$AUTO_PREPARE_THRESHOLD" \
      -e CLAWGUARD_ENRICHMENT_DAILY_CAP="$ENRICHMENT_DAILY_CAP" \
      -e CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE="$DIGEST_MAX_RESULTS_PER_SITE" \
      -e CLAWGUARD_DIGEST_TOP_MATCH_LIMIT="$TOP_MATCH_LIMIT" \
      -e CLAWGUARD_EMAIL_FROM="$EMAIL_FROM" \
      -e CLAWGUARD_EMAIL_PASSWORD="$EMAIL_PASS" \
      -e CLAWGUARD_DATA_DIR="/data/clawguard" \
      -w "$SKILL_DIR" \
      "$CONTAINER" \
      python3 job_search_secure.py digest \
        --compile \
        --format telegram \
        --no-prepare \
      2>&1 | tee "$LOG_DIR/compile_${DATE}.log"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e

    if [ "$EXIT_CODE" -eq 0 ] && [ -x "$POST_COMPILE_HOOK" ]; then
        set +e
        "$POST_COMPILE_HOOK" 2>&1 | tee -a "$LOG_DIR/post_compile_${DATE}.log"
        POST_EXIT=${PIPESTATUS[0]}
        set -e
        if [ "$POST_EXIT" -ne 0 ]; then
            echo "[$TIMESTAMP] post-compile hook failed (exit=$POST_EXIT)" | tee -a "$LOG_DIR/cron.log"
        fi
    elif [ "$EXIT_CODE" -eq 0 ]; then
        echo "[$TIMESTAMP] post-compile hook not found or not executable: $POST_COMPILE_HOOK" | tee -a "$LOG_DIR/cron.log"
    fi
else
    # Search single site, store to DB.
    set +e
    docker exec \
      -e OXYLABS_AISTUDIO_API_KEY="$API_KEY" \
      -e BRAVE_SEARCH_API_KEY="$BRAVE_API_KEY" \
      -e USAJOBS_AUTH_KEY="$USAJOBS_KEY" \
      -e USAJOBS_USER_AGENT="$USAJOBS_AGENT" \
      -e CLAWGUARD_SEARCH_PROVIDER="$SEARCH_PROVIDER" \
      -e CLAWGUARD_DISABLE_OXYLABS="$DISABLE_OXYLABS" \
      -e CLAWGUARD_FALLBACK_ON_EMPTY="$FALLBACK_ON_EMPTY" \
      -e CLAWGUARD_AUTO_PREPARE_THRESHOLD="$AUTO_PREPARE_THRESHOLD" \
      -e CLAWGUARD_ENRICHMENT_DAILY_CAP="$ENRICHMENT_DAILY_CAP" \
      -e CLAWGUARD_DIGEST_MAX_RESULTS_PER_SITE="$DIGEST_MAX_RESULTS_PER_SITE" \
      -e CLAWGUARD_DIGEST_TOP_MATCH_LIMIT="$TOP_MATCH_LIMIT" \
      -e CLAWGUARD_DATA_DIR="/data/clawguard" \
      -w "$SKILL_DIR" \
      "$CONTAINER" \
      python3 job_search_secure.py digest \
        --site "$SITE" \
        --budget 2 \
        --max-results-per-site "$DIGEST_MAX_RESULTS_PER_SITE" \
        --no-notify \
      2>&1 | tee "$LOG_DIR/search_${SITE}_${DATE}.log"
    EXIT_CODE=${PIPESTATUS[0]}
    set -e
fi

echo "[$TIMESTAMP] $SITE completed (exit=$EXIT_CODE)" | tee -a "$LOG_DIR/cron.log"
exit "$EXIT_CODE"
