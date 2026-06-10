#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose -f docker-compose-prod.yml"
APP_CONTAINER="iam_app"
VERSION="$(git describe --tags --always)"

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
fail() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

rollback() {
  log "Rollback for previous version"
  if docker image inspect iam:prev >/dev/null 2>&1; then
    docker tag iam:prev iam:prod
    $COMPOSE up -d app
    log "Rolled back to iam:prev"
  else
    log "skip rollback"
  fi
}

log "Preflight checks"
[ -f secrets/prod.enc.env ]  	|| fail "secrets/prod.enc.env tidak ada"
[ -d runtime/keys ]  		      || fail "runtime/keys/ tidak ada"

log "Decrypt secret"
sops -d secrets/prod.enc.env > runtime/.env

log "Build image"
docker image inspect iam:prod >/dev/null 2>&1 && docker tag iam:prod iam:prev || true
$COMPOSE build
docker tag iam:prod "iam:$VERSION"
log "Image version: $VERSION"

log "Start mysql + redis"
$COMPOSE up -d mysql redis

log "Migrate + seed"
$COMPOSE --profile tools run --rm migrate

log "Start app + cloudflared"
$COMPOSE up -d

log "Tunggu app healthy"
for i in $(seq 1 30); do
  status=$(docker inspect --format '{{.State.Health.Status}}' "$APP_CONTAINER" 2>/dev/null || echo "starting")
  [ "$status" = "healthy" ] && { log "App healthy ✓"; exit 0; }
  printf '  ... %s (%d/30)\n' "$status" "$i"
  sleep 2
done

rollback
fail "App ga healthy dalam 60s. Cek: $COMPOSE logs app"
