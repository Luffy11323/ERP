#!/usr/bin/env bash
# ==============================================================================
# Stream Local 1:1 Database directly into Frappe Cloud MariaDB & Setup Admin
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Target Frappe Cloud Database Credentials
FC_HOST="${FC_HOST:-n1-falkenstein-3.frappe.cloud}"
FC_PORT="${FC_PORT:-3306}"
FC_USER="${FC_USER:-fedea5f716a0953}"
FC_PASS="${FC_PASS:-6e3bacebd9fac2e4f3e4}"
FC_DB="${FC_DB:-_21953a8194dbd2c8}"

# Locate latest backup .sql.gz
BACKUP_FILE=""
if [ -d "/mnt/c/Users/Administrator/Desktop/Radiant_ERP_Backup/database_backup/new" ]; then
    BACKUP_FILE="$(ls -t /mnt/c/Users/Administrator/Desktop/Radiant_ERP_Backup/database_backup/new/*-database.sql.gz 2>/dev/null | head -1 || true)"
fi
if [ -z "$BACKUP_FILE" ] && [ -d "$SCRIPT_DIR/../../sites/akatech.local/private/backups" ]; then
    BACKUP_FILE="$(ls -t "$SCRIPT_DIR/../../sites/akatech.local/private/backups"/*-database.sql.gz 2>/dev/null | head -1 || true)"
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Could not find database backup .sql.gz file!" >&2
    exit 1
fi

echo "============================================================"
echo " Streaming Database to Frappe Cloud"
echo " File:   $BACKUP_FILE"
echo " Target: $FC_USER@$FC_HOST:$FC_PORT ($FC_DB)"
echo "============================================================"

# 1. Stream SQL dump into Frappe Cloud MariaDB
zcat "$BACKUP_FILE" | mysql -h "$FC_HOST" -P "$FC_PORT" -u "$FC_USER" -p"$FC_PASS" "$FC_DB"

echo "Database streamed successfully."

echo "============================================================"
echo " Setting Administrator User & Password (123)"
echo "============================================================"

# 2. Inject Administrator user, roles, and password hash for 123
mysql -h "$FC_HOST" -P "$FC_PORT" -u "$FC_USER" -p"$FC_PASS" "$FC_DB" -e "
INSERT INTO \`tabUser\` (
    name, email, first_name, username, enabled, user_type, send_welcome_email, creation, modified, modified_by, owner
) VALUES (
    'Administrator', 'admin@example.com', 'Administrator', 'administrator', 1, 'System User', 0, NOW(), NOW(), 'Administrator', 'Administrator'
) ON DUPLICATE KEY UPDATE enabled = 1;

INSERT IGNORE INTO \`tabHas Role\` (name, parent, parenttype, parentfield, role, creation, modified, modified_by, owner)
VALUES 
(REPLACE(UUID(),'-',''), 'Administrator', 'User', 'roles', 'System Manager', NOW(), NOW(), 'Administrator', 'Administrator'),
(REPLACE(UUID(),'-',''), 'Administrator', 'User', 'roles', 'Administrator', NOW(), NOW(), 'Administrator', 'Administrator');

DELETE FROM \`__Auth\` WHERE doctype = 'User' AND name = 'Administrator' AND fieldname = 'password';

INSERT INTO \`__Auth\` (doctype, name, fieldname, password, encrypted)
VALUES ('User', 'Administrator', 'password', '\$pbkdf2-sha256\$29000\$1BojRAhBqPWec04pBQDAuA\$wdZVtzCoeS9X7bmmzPjplfmsPWkR/8B1EqaD/LhBHGg', 0);
"

echo "Done! You can now log into Frappe Cloud with Administrator / 123."
