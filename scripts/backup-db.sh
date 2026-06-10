#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-/home/yudha/hdd/backup/iam}"
MOUNT="/home/yudha/hdd"

mountpoint -q "$MOUNT" || { echo "ERROR: partisi $MOUNT belum ter-mount" >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
OUT="$BACKUP_DIR/$(date +%F-%H%M).sql.gz"

docker exec iam_mysql sh -c \
    'exec mysqldump --single-transaction -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
    | gzip > "$OUT"

# off-site sync
if command -v rclone > /dev/null; then
    rclone copy "$BACKUP_DIR" r2:iam-backups/iam
fi

find "$BACKUP_DIR" -name '*.sql.gz' -mtime +14 -delete
echo "backup → $OUT"