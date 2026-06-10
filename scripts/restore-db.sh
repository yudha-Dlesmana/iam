#!/usr/bin/env bash
set -euo pipefail

FILE="${1:-}"
[ -n "$FILE" ] || { echo "Usage: $0 <backup.sql.gz>" >&2; exit 1; }
[ -f "$FILE" ] || { echo "ERROR: file '$FILE' not found" >&2; exit 1;}

# Konfirmasi — restore NIMPA data sekarang
echo "⚠️  Restore '$FILE'  database prod."
read -rp "Ketik 'yes' untuk lanjut: " ans
[ "$ans" = "yes" ] || { echo "Dibatalkan."; exit 1; }

echo "==> Backup current state ..."
bash "$(dirname "$0")/backup-db.sh"


echo "==> Restoring from $FILE..."
gunzip < "$FILE" | docker exec -i iam_mysql sh -c \
  'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

echo "==> DONE."