# DEPLOYMENT

What you need to change in this codebase (and around it) to make it deploy-ready. Host-specific plumbing — secret stores, file mounts, ingress, TLS — is your own platform's concern; this doc only covers the app side.

---

## 1. Rotate secrets first

Treat every value in your local `.env` and every file under `keys/` as compromised. Before pushing to any non-local environment:

```bash
# New HS256 secret for refresh tokens
python -c "import secrets; print(secrets.token_hex(32))"

# Fresh RSA keypair for access-token signing
bash scripts/gen_keys.sh iam-key-prod-1
```

Re-issue `GOOGLE_CLIENT_SECRET` in the Google Cloud Console (when OAuth lands).

---

## 2. Required environment variables

The app reads everything via `src/core/config.py`. Set these in your deploy target (env vars, secret manager, whatever your host uses):

| Var | Required | Example | Why |
|---|---|---|---|
| `ENV` | yes | `production` | Anything other than `development` enables HSTS, INFO logs, `proxy_headers=True`, masks health detail. |
| `HOST` | yes | `0.0.0.0` | Default is `localhost` — must bind 0.0.0.0 inside a container. |
| `PORT` | yes | `8000` | App port. |
| `FRONTEND_URLs` | yes | `https://app.example.com` | Comma-separated CORS origins. |
| `COOKIE_DOMAIN` | yes | `.example.com` | Refresh-token cookie domain. Blank only for same-host setups. |
| `FORWARDED_ALLOW_IPS` | yes | `127.0.0.1` | IPs allowed to set `X-Forwarded-For`. Pin to your reverse proxy. **Never** `*` unless your platform guarantees only the platform can reach the container (e.g. Cloud Run). |
| `DB_URL` | yes | `mysql+aiomysql://u:p@host:3306/db` | Async MySQL DSN. |
| `REDIS_URL` | yes | `rediss://:pwd@host:6380/0` | Sessions, rate limit, revocation, audit context. |
| `JWT_KEYS_DIR` | yes | `/app/keys` | Directory containing `<kid>/{private,public}.pem`. |
| `JWT_ACTIVE_KID` | yes | `iam-key-prod-1` | Must be a subdirectory of `JWT_KEYS_DIR`. |
| `JWT_ISSUER` | yes | `iam` | Token `iss` claim. Downstream services hardcode this. |
| `JWT_REFRESH_SECRET` | yes | 64-char hex | HS256 secret for refresh tokens. |
| `TEST_DB_URL` | no | — | Not needed in prod. |
| `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` | optional | — | Only when OAuth router is wired. |

`.env.example` lists every one of these.

---

## 3. Build the container

A multistage `Dockerfile` ships at the repo root. Builder stage compiles dependencies; runtime stage is `python:3.11-slim` with a non-root `app` user.

```bash
docker build -t iam:<tag> .
```

Default `CMD` is `python main.py` — `main.py` calls `uvicorn.run(...)` reading `HOST`, `PORT`, `ENV`, `FORWARDED_ALLOW_IPS` from the environment.

`.dockerignore` keeps `.venv`, `keys/`, `tests/`, dev docs, and `.env*` out of the image.

---

## 4. JWT signing keys

The app refuses to start if `JWT_KEYS_DIR/<JWT_ACTIVE_KID>/private.pem` is missing (`src/core/keys.py` raises `RuntimeError` at import). You have three options for getting the PEMs into the container — pick whichever your platform supports:

1. **Mounted secret volume** — store each PEM as a secret on your host, mount at `/app/keys/<kid>/private.pem` and `/public.pem`. Set `JWT_KEYS_DIR=/app/keys`.
2. **Init container / startup script** writes the keys to a shared volume before the app starts.
3. **Bake into image** — last resort, only with a private registry and audit trail.

Never reuse dev keys in any non-dev environment. Run `scripts/gen_keys.sh` for every new env.

### Rotating the active key

```
1. scripts/gen_keys.sh iam-key-prod-2          # new dir under JWT_KEYS_DIR
2. Deploy with both kids mounted, JWT_ACTIVE_KID unchanged
   → JWKS now publishes both public keys
3. Wait for downstream services to refresh their JWKS cache
4. Deploy with JWT_ACTIVE_KID=iam-key-prod-2
   → new tokens sign with new kid, old tokens still verify
5. Wait ACCESS_TTL (15 min) so live tokens drain
6. Next deploy: remove the old kid
```

`src/core/keys.py` loads kids once and caches (lru_cache). Rotation happens via redeploy. A `keys.reload()` helper exists for tests and operational tooling.

---

## 5. Run migrations as a separate step

Migrations are **not** applied on app boot. Run them as a one-shot job at the same image tag as the app, before scaling app instances up:

```bash
docker run --rm --env-file .env iam:<tag> alembic upgrade head
```

First-ever deploy also needs the seeder once (idempotent — safe to re-run, but it never deletes records that vanish from the seeder lists):

```bash
docker run --rm --env-file .env iam:<tag> python -m scripts.seed
```

---

## 6. Reverse proxy / TLS

The app does not terminate TLS itself. Your platform's proxy / LB does. The app expects:

- `X-Forwarded-For` set by the proxy with the real client IP first.
- The proxy **strips any client-supplied** `X-Forwarded-*` headers before forwarding — otherwise clients can spoof source IP and bypass the rate limiter / audit log.
- `FORWARDED_ALLOW_IPS` pinned to the proxy's IP (or `*` only when the platform guarantees nothing else can reach the container).
- HTTPS on the public side; the app talks plain HTTP behind the proxy.

`_client_ip()` in `src/routers/auth.py` and the audit middleware in `src/core/audit_middleware.py` both read `X-Forwarded-For` first-hop. With `FORWARDED_ALLOW_IPS` correctly pinned and `proxy_headers=True` (auto-enabled when `ENV != development`), the real client IP flows through to the rate limiter and audit log.

Security headers (HSTS in prod, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`) are emitted by `src/core/security_headers.py` — no proxy config needed for those.

---

## 7. Health checks

`GET /v1/health` returns 200 with a JSON status per dependency (DB, Redis). Use it for both liveness and readiness probes. In production the response intentionally hides exception detail — only `{"status": "ok|degraded"}` per component. Server logs still record full traces via `log.exception`.

---

## 8. Post-deploy checklist

- [ ] `GET /v1/health` returns 200 from inside the container and from the public URL.
- [ ] `GET /.well-known/jwks.json` lists the expected kid(s).
- [ ] Log in as the seeded super_admin, get an access token, call `/v1/auth/current-user`.
- [ ] Response headers include HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (`curl -I`).
- [ ] CORS preflight from the real frontend origin succeeds; an unrelated origin is rejected.
- [ ] Rate limit fires after 5 wrong passwords on `/v1/auth/login` (429 + `Retry-After`).
- [ ] An audit row appears for a role mutation: `GET /v1/audit-logs`.
- [ ] `POST /v1/users/{id}/revoke-tokens` causes that user's existing access token to return 401.
- [ ] `alembic current` on the deployed DB matches `head`.

---

## 9. Known limitations to address later

Tracked in [TODO.md](TODO.md). None block a small-scale launch:

- Google OAuth router not wired (model + env vars exist).
- Logs are plain text — JSON helps log aggregators.
- No request-ID middleware — cross-service log correlation is manual.
- `/v1/health` is one endpoint for liveness + readiness; LBs may want a split later.
- No global per-IP rate limit beyond `/v1/auth/login`.
- Secrets manager integration is your platform's job — code reads only from env vars.
