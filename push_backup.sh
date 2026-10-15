#!/bin/bash
# Push the latest database + public files + private files backup to
#   https://github.com/Luffy11323/Backup   (separate repo, NOT the production ERP repo)
#
# Usage (WSL):   bash /home/administrator/frappe-bench/apps/akatech_erp/push_backup.sh [--no-new]
#   default  : creates a fresh `bench backup --with-files`, then pushes it
#   --no-new : pushes the newest existing trio without creating a new backup
#
# Never force-pushes. Working tree keeps only the latest trio (git history keeps older ones).
set -euo pipefail

BENCH=/home/administrator/frappe-bench
SITE=akatech.local
BK=$BENCH/sites/$SITE/private/backups
REPO=/home/administrator/Backup_repo
REMOTE=https://github.com/Luffy11323/Backup

cd "$BENCH"
if [ "${1:-}" != "--no-new" ]; then
  bench --site "$SITE" backup --with-files
fi

DB=$(ls -t "$BK"/*-database.sql.gz | head -1)
PRIV=$(ls -t "$BK"/*-private-files.tar | head -1)
PUB=$(ls -t "$BK"/*-files.tar | grep -v -- '-private-files.tar' | head -1)
echo "db:      $DB"; echo "public:  $PUB"; echo "private: $PRIV"

if [ ! -d "$REPO/.git" ]; then
  mkdir -p "$REPO"
  git -C "$REPO" init -q -b main
  git -C "$REPO" remote add origin "$REMOTE"
fi
cd "$REPO"
# sync with remote if it already has commits (fast-forward only)
if git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git fetch -q origin main
  git merge -q --ff-only origin/main 2>/dev/null || git reset -q --soft origin/main
fi

cp "$DB"   database.sql.gz
cp "$PUB"  public-files.tar
cp "$PRIV" private-files.tar
cat > LATEST.txt <<EOF
Backup of site $SITE, created $(date '+%F %T')
database : $(basename "$DB")  ($(du -h "$DB" | cut -f1))
public   : $(basename "$PUB")  ($(du -h "$PUB" | cut -f1))
private  : $(basename "$PRIV")  ($(du -h "$PRIV" | cut -f1))
Restore  : Frappe Cloud -> site -> Restore with files (database.sql.gz, public-files.tar, private-files.tar)
EOF

for f in database.sql.gz public-files.tar private-files.tar; do
  if [ "$(stat -c %s "$f")" -gt 95000000 ]; then
    echo "WARNING: $f is over 95 MB; GitHub rejects files over 100 MB. Use Git LFS or a release asset." >&2
  fi
done

git add -A
git commit -q -m "Backup $(date '+%F %H:%M') - db + public + private" || echo "nothing new to commit"
git push -u origin main
git log --oneline -1
