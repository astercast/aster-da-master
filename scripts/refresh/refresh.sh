#!/usr/bin/env bash
# refresh.sh — cron-ready entry point for the play-count refresh pipeline.
#
# Usage:
#   bash scripts/refresh/refresh.sh            # weekly refresh (tiers a-c)
#   bash scripts/refresh/refresh.sh --merge     # apply snapshot -> data/artist.json
#
# Appends timestamped output to logs/refresh.log. Exit code is the Python
# script's exit code (0 on success or graceful skip, 1 on hard errors).
#
# Cron (weekly, Sundays 09:00 UTC) — see GO_LIVE.md:
#   0 9 * * 0 cd /path/to/aster-da-master && bash scripts/refresh/refresh.sh

set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO" || { echo "ERROR: cannot cd to repo root" >&2; exit 1; }
mkdir -p logs

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

{
  echo "[$TS] refresh start (args: $*)"
  python3 scripts/refresh/refresh_plays.py "$@"
  RC=$?
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] refresh done (exit=$RC)"
  exit "$RC"
} >> logs/refresh.log 2>&1
