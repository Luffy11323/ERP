#!/usr/bin/env bash
# ==============================================================================
# Akatech ERP — 1-Command Sync / Scraper Runner
# ==============================================================================
# This script runs the full 1:1 sync pipeline from Radiant Medical into the local
# ERP site. It is crash-safe, idempotent, and resumes where it left off.
#
# Usage:
#   ./run_sync.sh                # Normal sync (upserts, deletions, files, verify)
#   ./run_sync.sh --dry-run      # Preview only: checks counts without writing
#   ./run_sync.sh --with-backup  # Runs sync, then automatically pushes DB/files to Luffy11323/Backup
#   ./run_sync.sh --skip-files   # Syncs database records only, skips file downloads
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

# 1. Check for .env credentials
if [ ! -f "$APP_DIR/.env" ] && [ -z "${RADIANT_API_KEY:-}" ]; then
    echo "ERROR: Credentials not found!" >&2
    echo "Please copy .env.example to .env and fill in your RADIANT_API_KEY and RADIANT_API_SECRET:" >&2
    echo "  cp $APP_DIR/.env.example $APP_DIR/.env" >&2
    exit 1
fi

# 2. Locate Frappe Bench environment
BENCH_DIR=""
PYTHON_BIN=""

if [ -d "$APP_DIR/../../sites" ] && [ -x "$APP_DIR/../../env/bin/python" ]; then
    BENCH_DIR="$(cd "$APP_DIR/../.." && pwd)"
    PYTHON_BIN="$BENCH_DIR/env/bin/python"
elif [ -d "/home/administrator/frappe-bench" ]; then
    BENCH_DIR="/home/administrator/frappe-bench"
    PYTHON_BIN="$BENCH_DIR/env/bin/python"
else
    # Fallback to python3 in PATH if run in standalone mode
    PYTHON_BIN="$(which python3 || which python)"
fi

echo "============================================================"
echo " Starting Akatech ERP Sync Pipeline"
echo " Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo " Python: $PYTHON_BIN"
[ -n "$BENCH_DIR" ] && echo " Bench:  $BENCH_DIR"
echo "============================================================"

WITH_BACKUP=false
ARGS=()

for arg in "$@"; do
    if [ "$arg" == "--with-backup" ]; then
        WITH_BACKUP=true
    else
        ARGS+=("$arg")
    fi
done

# 3. Execute the sync
if [ -n "$BENCH_DIR" ]; then
    cd "$BENCH_DIR/sites"
    "$PYTHON_BIN" -m akatech_erp.monthly_sync "${ARGS[@]}"
else
    cd "$APP_DIR"
    "$PYTHON_BIN" -m akatech_erp.monthly_sync "${ARGS[@]}"
fi

# 4. Optional automatic backup push
if [ "$WITH_BACKUP" = true ]; then
    echo ""
    echo "============================================================"
    echo " Sync finished. Pushing backup to Luffy11323/Backup..."
    echo "============================================================"
    if [ -f "$APP_DIR/push_backup.sh" ]; then
        bash "$APP_DIR/push_backup.sh"
    fi
fi

echo ""
echo "Done!"
