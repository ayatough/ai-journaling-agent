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
    echo "[checkin] $(date -u +%Y-%m-%dT%H:%M:%SZ) $(uv run checkin run 2>&1)"
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
