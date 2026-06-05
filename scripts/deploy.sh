#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SOPS_AGE_KEY_FILE:?set SOPS_AGE_KEY_FILE ke age key (mis. ~/.config/iam/age.key)}"
command -v sops >/dev/null || { echo "sops required"; exit 1; }

COMPOSE="docker compose -f docker-compose-prod.yml"
RUNTIME=runtime
ENV_OUT="$RUNTIME/.env"
KEYS_OUT="$RUNTIME/keys"

umask 077
echo "== decrypt secret -> $RUNTIME/"
rm -rf "$RUNTIME"
mkdir -p "$KEYS_OUT"
sops -d secrets/production.env > "$ENV_OUT"

for kdir in secrets/keys/*/; do
    kid="$(basename "$kdir")"
    mkdir -p "$KEYS_OUT/$kid"
    sops -d --input-type binary --output-type binary "$kdir/private.pem" > "$KEYS_OUT/$kid/private.pem"
    cp "$kdir/public.pem" "$KEYS_OUT/$kid/public.pem"
    echo " + $kid"
done

echo "== build"
$COMPOSE --env-file "$ENV_OUT" build

echo "== start db + redis (healthy)"
$COMPOSE --env-file "$ENV_OUT" up -d --wait mysql redis

echo "== migrate + seed"
$COMPOSE --env-file "$ENV_OUT" run --rm migrate

echo "== up"
$COMPOSE --env-file "$ENV_OUT" up -d app

echo "== DONE, check: curl http://localhost:9001/v1/health"