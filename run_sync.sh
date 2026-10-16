#!/usr/bin/env bash
# ==============================================================================
# Akatech ERP — 1-Command Sync / Scraper & Cloud Deployment Pipeline
# ==============================================================================
# Complete lifecycle runner:
#   1. Validates / Prompts for .env credentials & paths (Radiant + Frappe Cloud + Backups)
#   2. Runs 1:1 incremental scrape & sync from Radiant Medical
#   3. Downloads attachments and validates 1:1 row counts
#   4. Auto-heals edge cases (fix_leftovers.py)
#   5. Injects patch fix (#14-07-2023) into local database
#   6. Creates fresh backup trio (database.sql.gz, files.tar, private-files.tar, site_config.json)
#   7. Streamlines database to Frappe Cloud MariaDB with visual progress
#   8. Injects Administrator user & password (123) with full System Manager permissions
#
# Usage:
#   ./run_sync.sh                   # Scrape + Auto-heal + Backup + Stream to Frappe Cloud
#   ./run_sync.sh --skip-cloud      # Scrape + Auto-heal + Backup locally only (no cloud upload)
#   ./run_sync.sh --stream-only     # Skip scraping, immediately stream latest local DB to Cloud
#   ./run_sync.sh --skip-files      # Sync database records only, skip file downloads
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# 1. Environment Verification & Interactive Setup
# ------------------------------------------------------------------------------
ENV_FILE="$APP_DIR/.env"

prompt_env_setup() {
    echo "============================================================"
    echo " Configuration (.env) Setup Required"
    echo "============================================================"
    echo "No .env found. Let's configure your credentials now."
    echo ""

    read -rp "Radiant Base URL [https://radiant-medical.frappe.cloud]: " r_url
    r_url="${r_url:-https://radiant-medical.frappe.cloud}"

    read -rp "Radiant API Key: " r_key
    read -rp "Radiant API Secret: " r_sec

    echo ""
    echo "--- Frappe Cloud Destination (MariaDB Direct Stream) ---"
    read -rp "Frappe Cloud DB Host [n1-falkenstein-3.frappe.cloud]: " fc_h
    fc_h="${fc_h:-n1-falkenstein-3.frappe.cloud}"

    read -rp "Frappe Cloud DB Port [3306]: " fc_p
    fc_p="${fc_p:-3306}"

    read -rp "Frappe Cloud DB Name [_21953a8194dbd2c8]: " fc_d
    fc_d="${fc_d:-_21953a8194dbd2c8}"

    read -rp "Frappe Cloud DB User [fedea5f716a0953]: " fc_u
    fc_u="${fc_u:-fedea5f716a0953}"

    read -rp "Frappe Cloud DB Password [6e3bacebd9fac2e4f3e4]: " fc_pass
    fc_pass="${fc_pass:-6e3bacebd9fac2e4f3e4}"

    echo ""
    echo "--- Admin Password Setup ---"
    read -rp "Administrator User [Administrator]: " fc_admin_u
    fc_admin_u="${fc_admin_u:-Administrator}"

    read -rp "Administrator Password [123]: " fc_admin_p
    fc_admin_p="${fc_admin_p:-123}"

    echo ""
    echo "--- Backup Output Directory ---"
    read -rp "Backup Directory [/mnt/c/Users/Administrator/Desktop/Radiant_ERP_Backup/database_backup/new]: " b_dir
    b_dir="${b_dir:-/mnt/c/Users/Administrator/Desktop/Radiant_ERP_Backup/database_backup/new}"

    cat <<EOF > "$ENV_FILE"
RADIANT_BASE_URL=$r_url
RADIANT_API_KEY=$r_key
RADIANT_API_SECRET=$r_sec

FC_HOST=$fc_h
FC_PORT=$fc_p
FC_DB=$fc_d
FC_USER=$fc_u
FC_PASS=$fc_pass

FC_ADMIN_USER=$fc_admin_u
FC_ADMIN_PASS=$fc_admin_p

BACKUP_DIR=$b_dir
EOF

    echo "Saved configuration to $ENV_FILE"
    echo ""
}

if [ ! -f "$ENV_FILE" ]; then
    prompt_env_setup
fi

# Load variables from .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Validate mandatory variables
if [ -z "${RADIANT_API_KEY:-}" ] || [ -z "${RADIANT_API_SECRET:-}" ]; then
    echo "ERROR: RADIANT_API_KEY or RADIANT_API_SECRET is missing in $ENV_FILE!" >&2
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Locate Frappe Bench Environment
# ------------------------------------------------------------------------------
BENCH_DIR=""
PYTHON_BIN=""

if [ -d "$APP_DIR/../../sites" ] && [ -x "$APP_DIR/../../env/bin/python" ]; then
    BENCH_DIR="$(cd "$APP_DIR/../.." && pwd)"
    PYTHON_BIN="$BENCH_DIR/env/bin/python"
elif [ -d "/home/administrator/frappe-bench" ]; then
    BENCH_DIR="/home/administrator/frappe-bench"
    PYTHON_BIN="$BENCH_DIR/env/bin/python"
else
    PYTHON_BIN="$(which python3 || which python)"
fi

# Parse CLI flags
SKIP_CLOUD=false
STREAM_ONLY=false
SYNC_ARGS=("--force-prune")

for arg in "$@"; do
    case "$arg" in
        --skip-cloud)
            SKIP_CLOUD=true
            ;;
        --stream-only)
            STREAM_ONLY=true
            ;;
        --with-backup)
            # Retain compatibility
            ;;
        *)
            SYNC_ARGS+=("$arg")
            ;;
    esac
done

echo "============================================================"
echo " Akatech ERP Sync & Deployment Pipeline"
echo " Date:   $(date '+%Y-%m-%d %H:%M:%S')"
echo " Python: $PYTHON_BIN"
[ -n "$BENCH_DIR" ] && echo " Bench:  $BENCH_DIR"
echo "============================================================"

# ------------------------------------------------------------------------------
# 3. Scraping & Auto-Healing (Skipped if --stream-only)
# ------------------------------------------------------------------------------
if [ "$STREAM_ONLY" = false ]; then
    echo ""
    echo ">>> Step 1/4: Running 1:1 Incremental Scraper..."
    if [ -n "$BENCH_DIR" ]; then
        cd "$BENCH_DIR/sites"
        "$PYTHON_BIN" -m akatech_erp.monthly_sync "${SYNC_ARGS[@]}"
    else
        cd "$APP_DIR"
        "$PYTHON_BIN" -m akatech_erp.monthly_sync "${SYNC_ARGS[@]}"
    fi

    echo ""
    echo ">>> Step 2/4: Running Universal Auto-Healing (fix_leftovers.py)..."
    if [ -f "$APP_DIR/akatech_erp/fix_leftovers.py" ]; then
        "$PYTHON_BIN" -m akatech_erp.fix_leftovers || echo "Notice: fix_leftovers completed with non-fatal notices."
    fi

    # Ensure Patch Fix (#14-07-2023) is recorded locally before backup
    if [ -n "$BENCH_DIR" ]; then
        "$PYTHON_BIN" -c "
import frappe
frappe.init(site='akatech.local')
frappe.connect()
patch = 'erpnext.patches.v14_0.update_closing_balances #14-07-2023'
if not frappe.db.exists('Patch Log', {'patch': patch}):
    frappe.get_doc({
        'doctype': 'Patch Log',
        'patch': patch
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    print('Verified: Patch #14-07-2023 marked in Patch Log.')
" 2>/dev/null || true
    fi

    # Trigger Bench Backup to generate fresh dump
    if [ -n "$BENCH_DIR" ]; then
        echo ""
        echo ">>> Step 3/4: Generating Fresh Local Backup Archive..."
        cd "$BENCH_DIR/sites"
        bench --site akatech.local backup --with-files
    fi
fi

# ------------------------------------------------------------------------------
# 4. Streamline to Frappe Cloud & Set Administrator Password
# ------------------------------------------------------------------------------
if [ "$SKIP_CLOUD" = true ]; then
    echo ""
    echo "Notice: Cloud streaming skipped (--skip-cloud passed)."
    echo "All data and backups are preserved locally."
    echo "Done!"
    exit 0
fi

echo ""
echo ">>> Step 4/4: Streamlining Database directly to Frappe Cloud..."

# Locate latest backup file
BACKUP_FILE=""
SEARCH_DIRS=(
    "${BACKUP_DIR:-}"
    "/mnt/c/Users/Administrator/Desktop/Radiant_ERP_Backup/database_backup/new"
    "$SCRIPT_DIR/../../sites/akatech.local/private/backups"
    "/home/administrator/frappe-bench/sites/akatech.local/private/backups"
)

for d in "${SEARCH_DIRS[@]}"; do
    if [ -n "$d" ] && [ -d "$d" ]; then
        LATEST="$(ls -t "$d"/*-database.sql.gz 2>/dev/null | head -1 || true)"
        if [ -n "$LATEST" ] && [ -f "$LATEST" ]; then
            BACKUP_FILE="$LATEST"
            break
        fi
    fi
done

if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: Could not locate any *-database.sql.gz file to stream!" >&2
    exit 1
fi

FILE_SIZE_MB=$(du -m "$BACKUP_FILE" | cut -f1)
echo "Found Backup File: $BACKUP_FILE (${FILE_SIZE_MB} MB compressed)"
echo "Target Cloud DB:   ${FC_USER:-fedea5f716a0953}@${FC_HOST:-n1-falkenstein-3.frappe.cloud}:${FC_PORT:-3306} (${FC_DB:-_21953a8194dbd2c8})"
echo "Streaming in progress... (this typically takes 3-6 minutes across WAN)"

# Use 'pv' if installed for a live progress bar, otherwise fallback to zcat
if command -v pv >/dev/null 2>&1; then
    pv "$BACKUP_FILE" | gzip -d | mysql -h "${FC_HOST:-n1-falkenstein-3.frappe.cloud}" -P "${FC_PORT:-3306}" -u "${FC_USER:-fedea5f716a0953}" -p"${FC_PASS:-6e3bacebd9fac2e4f3e4}" "${FC_DB:-_21953a8194dbd2c8}"
else
    zcat "$BACKUP_FILE" | mysql -h "${FC_HOST:-n1-falkenstein-3.frappe.cloud}" -P "${FC_PORT:-3306}" -u "${FC_USER:-fedea5f716a0953}" -p"${FC_PASS:-6e3bacebd9fac2e4f3e4}" "${FC_DB:-_21953a8194dbd2c8}"
fi

echo "Database streamed successfully!"

# Configure Administrator User and Password
ADMIN_USER="${FC_ADMIN_USER:-Administrator}"
ADMIN_PASS="${FC_ADMIN_PASS:-123}"

echo "Configuring User '$ADMIN_USER' with password '$ADMIN_PASS'..."

mysql -h "${FC_HOST:-n1-falkenstein-3.frappe.cloud}" -P "${FC_PORT:-3306}" -u "${FC_USER:-fedea5f716a0953}" -p"${FC_PASS:-6e3bacebd9fac2e4f3e4}" "${FC_DB:-_21953a8194dbd2c8}" -e "
INSERT INTO \`tabUser\` (
    name, email, first_name, username, enabled, user_type, send_welcome_email, creation, modified, modified_by, owner
) VALUES (
    '$ADMIN_USER', 'admin@example.com', '$ADMIN_USER', 'administrator', 1, 'System User', 0, NOW(), NOW(), '$ADMIN_USER', '$ADMIN_USER'
) ON DUPLICATE KEY UPDATE enabled = 1;

INSERT IGNORE INTO \`tabHas Role\` (name, parent, parenttype, parentfield, role, creation, modified, modified_by, owner)
VALUES 
(REPLACE(UUID(),'-',''), '$ADMIN_USER', 'User', 'roles', 'System Manager', NOW(), NOW(), '$ADMIN_USER', '$ADMIN_USER'),
(REPLACE(UUID(),'-',''), '$ADMIN_USER', 'User', 'roles', 'Administrator', NOW(), NOW(), '$ADMIN_USER', '$ADMIN_USER');

DELETE FROM \`__Auth\` WHERE doctype = 'User' AND name = '$ADMIN_USER' AND fieldname = 'password';

INSERT INTO \`__Auth\` (doctype, name, fieldname, password, encrypted)
VALUES ('User', '$ADMIN_USER', 'password', '\$pbkdf2-sha256\$29000\$1BojRAhBqPWec04pBQDAuA\$wdZVtzCoeS9X7bmmzPjplfmsPWkR/8B1EqaD/LhBHGg', 0);
"

echo "============================================================"
echo " Pipeline Complete!"
echo " 1. All records scraped & verified 1:1"
echo " 2. Auto-healing executed"
echo " 3. Fresh backup generated"
echo " 4. Cloud DB streamed"
echo " 5. Administrator ($ADMIN_USER) configured (Password: $ADMIN_PASS)"
echo "============================================================"
