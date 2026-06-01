# DEPLOYMENT

Production deployment guide for the IAM microservice. The app itself is host-agnostic — anywhere that runs a container + reaches MySQL 8 + Redis 7 works.

> Currently development-only. This doc is the **plan**, not a record of a deployed system. Pick a host before acting on the host-specific sections.

---

## 1. Pre-flight

Before going anywhere near a real environment:

1. **Rotate every secret** in `.env`. Treat the current values as compromised. Generate fresh ones:
   ```bash
   # JWT refresh secret (HS256)
   python -c "import secrets; print(secrets.token_hex(32))"

   # Fresh JWT signing keypair (private/public RSA)
   bash scripts/gen_keys.sh iam-key-prod-1
   ```
   Re-issue the Google OAuth client secret from the Google Cloud Console.

2. **Run the full test suite + lint** against a clean checkout:
   ```bash
   make install
   make gen-keys
   make upgrade
   make seed
   ruff check src tests
   pytest tests/ -v
   ```

3. **Build the image locally** and sanity-test it:
   ```bash
   docker build -t iam:local .
   docker run --rm --env-file .env -p 8000:8000 iam:local
   curl http://localhost:8000/v1/health
   ```

4. **Note all migrations** you need to apply on the target DB:
   ```bash
   alembic history --verbose
   ```

---

## 2. Required environment variables

All must be set in the target environment. None have safe defaults for production.

| Var | Required | Example | Notes |
|---|---|---|---|
| `ENV` | yes | `production` | Anything other than `development` enables prod behavior (HSTS, INFO logs, `proxy_headers=True`). |
| `HOST` | yes | `0.0.0.0` | Must bind 0.0.0.0 inside a container, not `localhost`. |
| `PORT` | yes | `8000` | Whatever your platform expects. |
| `FRONTEND_URLs` | yes | `https://app.example.com` | Comma-separated. CORS `allow_origins`. |
| `COOKIE_DOMAIN` | yes | `.example.com` | Refresh-token cookie domain. Leave blank only for same-host setups. |
| `FORWARDED_ALLOW_IPS` | yes | `127.0.0.1` or LB CIDR | IPs allowed to set `X-Forwarded-For`. **Never** set to `*` in production — that lets any client spoof source IP. Pin to your reverse proxy / LB. |
| `DB_URL` | yes | `mysql+aiomysql://u:p@host:3306/db?ssl=true` | Async DSN. Enable TLS via DSN params for managed DBs. |
| `TEST_DB_URL` | no | — | Not needed in prod containers. |
| `REDIS_URL` | yes | `rediss://:pwd@host:6380/0` | Use `rediss://` for TLS. Sessions, rate-limit, revocation, audit-context all rely on this. |
| `JWT_KEYS_DIR` | yes | `/app/keys` | Mounted dir containing `<kid>/{private,public}.pem`. |
| `JWT_ACTIVE_KID` | yes | `iam-key-prod-1` | Must match a subdirectory of `JWT_KEYS_DIR`. |
| `JWT_ISSUER` | yes | `iam` | Token `iss` claim. Downstream services hardcode this when validating. |
| `JWT_REFRESH_SECRET` | yes | 64-char hex | HS256 secret. Rotate independently of the RS256 keyset. |
| `GOOGLE_CLIENT_ID` | optional | — | Required only when OAuth router is wired (not yet). |
| `GOOGLE_CLIENT_SECRET` | optional | — | Same. |
| `GOOGLE_REDIRECT_URI` | optional | — | Same. |

---

## 3. JWT signing keys

The app refuses to start if `JWT_KEYS_DIR/<JWT_ACTIVE_KID>/private.pem` is missing. Three strategies, pick one:

1. **Mounted secret volume** (recommended on Kubernetes / Cloud Run / Fly.io machines):
   - Store private keys in your platform's secret manager (one secret per kid).
   - Mount them at `/app/keys/<kid>/private.pem` and `/public.pem`.
   - `JWT_KEYS_DIR=/app/keys`.

2. **Init container / sidecar** writes the keys to a shared volume before the app boots.

3. **Bake into image** (only acceptable for closed registries with audit). Not recommended.

The `keys/` directory is gitignored. Generate fresh keys per environment — never reuse dev keys in prod.

### Rotating keys

Add a new kid alongside the active one, deploy, then flip `JWT_ACTIVE_KID`:

```
1. scripts/gen_keys.sh iam-key-prod-2          # creates new dir under JWT_KEYS_DIR
2. Deploy with both kids mounted, JWT_ACTIVE_KID unchanged  → JWKS now publishes both
3. Wait for downstream services to refresh their JWKS cache
4. Deploy with JWT_ACTIVE_KID=iam-key-prod-2   → new tokens use new kid
5. Wait for ACCESS_TTL (15 min) so all live tokens drain
6. Remove the old kid in the next deploy
```

`src/core/keys.py` loads kids once at startup. A `reload()` helper exists for tests / operational use, but production rotation should happen via redeploy.

---

## 4. Database migrations

Migrations are **not** applied by the app on boot. Run them as a separate step in your release pipeline, before scaling the app up.

```bash
# Run-once container at the same image tag as the app:
docker run --rm --env-file .env iam:<tag> alembic upgrade head
```

For first-ever deploy you also need the seeder once:

```bash
docker run --rm --env-file .env iam:<tag> python -m scripts.seed
```

The seeder is idempotent (skips existing rows) so re-running is safe — but only run it in the bootstrap phase. Subsequent seed runs do not delete records that no longer appear in the seeder lists.

---

## 5. Container image

A multistage `Dockerfile` is included. It builds a slim runtime image (~150 MB) under a non-root `app` user, exposing port 8000.

```bash
docker build -t iam:<tag> .
docker tag iam:<tag> <registry>/iam:<tag>
docker push <registry>/iam:<tag>
```

CMD is `python main.py`. This reads `HOST`, `PORT`, `ENV` from env and runs uvicorn with `proxy_headers=True` when `ENV != development`.

---

## 6. Reverse proxy / TLS

The app does not terminate TLS itself. Put a proxy (NGINX, Caddy, Traefik, Cloud Run, ALB, etc.) in front:

- Terminate TLS at the proxy.
- Set `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` on requests.
- **Strip any client-supplied** `X-Forwarded-*` headers before forwarding — otherwise clients can spoof source IP and bypass the rate limiter / audit log.
- Forward to the app on its `PORT`.

The app's `_client_ip()` (used by login rate limit and audit middleware) reads `X-Forwarded-For` first-hop. Combined with `FORWARDED_ALLOW_IPS` pinned to the proxy, this gives the real client IP without spoofing risk.

HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` are emitted by the security headers middleware (`src/core/security_headers.py`) automatically when `ENV != development`.

---

## 7. Health checks

`GET /v1/health` returns 200 with a JSON status object, hitting MySQL + Redis. Use it as both liveness and readiness for now; the deeper split (light liveness vs. full readiness) is future work.

In production the response intentionally **does not** leak exception detail — only `{"status": "ok|degraded"}` per component. Server logs still record full traces.

---

## 8. Per-host recipes

### Fly.io

```bash
fly launch --no-deploy        # generates fly.toml; tweak as below
```

Add to `fly.toml`:
```toml
[env]
ENV = "production"
HOST = "0.0.0.0"
PORT = "8000"
JWT_KEYS_DIR = "/app/keys"
JWT_ACTIVE_KID = "iam-key-prod-1"
JWT_ISSUER = "iam"
FORWARDED_ALLOW_IPS = "127.0.0.1"

[[mounts]]
source = "iam_keys"
destination = "/app/keys"
```

Secrets (not in `fly.toml`):
```bash
fly secrets set JWT_REFRESH_SECRET=...
fly secrets set DB_URL=...
fly secrets set REDIS_URL=...
```

Upload private keys to the mounted volume separately via `fly ssh sftp` or via a release-command init.

Use a managed MySQL (PlanetScale / Aiven) and Redis (Upstash) rather than running them in Fly.

### Google Cloud Run

```bash
gcloud run deploy iam \
  --image <registry>/iam:<tag> \
  --region <region> \
  --set-env-vars ENV=production,HOST=0.0.0.0,PORT=8000,JWT_ISSUER=iam,FORWARDED_ALLOW_IPS=* \
  --set-secrets JWT_REFRESH_SECRET=jwt-refresh:latest,DB_URL=db-url:latest,REDIS_URL=redis-url:latest \
  --update-secrets /app/keys/iam-key-prod-1/private.pem=jwt-priv:latest,/app/keys/iam-key-prod-1/public.pem=jwt-pub:latest
```

Cloud Run sits behind Google's frontend; `FORWARDED_ALLOW_IPS=*` is safer there than elsewhere because nothing else can reach the container. Even so, prefer pinning when you can.

### Railway / Render

Both accept the Dockerfile directly. Set env vars in their dashboard. Mount keys via their secrets / file system feature. Use the platform's managed Redis + MySQL plugins or external managed services.

### Kubernetes (rough sketch)

- `Deployment` with `image`, `env`, `volumeMounts: /app/keys`.
- `Secret` of type `Opaque` carrying each `<kid>/private.pem` + `public.pem`, mounted as files.
- Separate `Job` for `alembic upgrade head` triggered pre-rollout.
- `Service` ClusterIP, `Ingress` with TLS for external access.
- Liveness + readiness probes on `/v1/health` (or split later).

---

## 9. Post-deploy checklist

- [ ] `GET /v1/health` returns 200 from inside and from the public URL.
- [ ] `GET /.well-known/jwks.json` lists the expected kid(s).
- [ ] Log in with the seeded super_admin; receive an access token; call `/v1/auth/current-user`.
- [ ] HSTS / nosniff / frame-options headers present on responses (`curl -I`).
- [ ] CORS preflight from the real frontend origin succeeds; an unrelated origin is rejected.
- [ ] Rate-limit fires after 5 wrong-password attempts (returns 429 + `Retry-After`).
- [ ] Audit log row appears for a role mutation: `GET /v1/audit-logs`.
- [ ] Revoke a test user, confirm their existing access token returns 401 within seconds.
- [ ] Migrations applied: `alembic current` on the deployed DB matches `head`.
- [ ] Rotate the **dev** secrets one more time after deploy — they were exposed during build.

---

## 10. Known limitations to address before high-traffic prod

- No request-id middleware → cross-service log correlation is manual.
- Logs are plain text, not JSON → log aggregators do extra parsing.
- `/v1/health` is one endpoint for liveness + readiness; LBs may want different semantics.
- Pagination capped at 100, but no per-IP request-rate limit beyond `/auth/login`.
- Secrets manager integration is not coded (env vars only) — handled by your platform's secret injection.
- Google OAuth router is not wired (model exists, no endpoint).

None block a small-scale launch. All are tracked in [TODO.md](TODO.md).
