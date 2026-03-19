#!/bin/sh
# scripts/run-checkin.sh
#
# Send a check-in LINE message if one is needed at the current time.
# Designed to run every 30 minutes (either via cron or --loop mode).
#
# Usage:
#   ./scripts/run-checkin.sh          # run once
#   ./scripts/run-checkin.sh --loop   # run every 30 minutes (for Docker)

set -e

run_once() {
    STATUS=$(uv run checkin status 2>&1)

    case "$STATUS" in
        *"check-in needed"*)
            KIND=$(echo "$STATUS" | head -1 | awk '{print $1}')
            PROMPT=$(echo "$STATUS" | grep "^Prompt:" | sed 's/^Prompt: //')
            echo "[checkin] $(date -u +%Y-%m-%dT%H:%M:%SZ) Sending $KIND check-in..."
            uv run push-line --text "$PROMPT"
            uv run checkin record --kind "$KIND" --text "$PROMPT"
            echo "[checkin] Done."
            ;;
        *)
            echo "[checkin] $(date -u +%Y-%m-%dT%H:%M:%SZ) No check-in needed."
            ;;
    esac
}

if [ "${1:-}" = "--loop" ]; then
    echo "[checkin] Starting loop (interval: 30 minutes)..."
    while true; do
        run_once
        sleep 1800
    done
else
    run_once
fi
