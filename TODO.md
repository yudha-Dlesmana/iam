# TODO

Deferred work for the IAM microservice. Tracked here so it isn't lost.

## Next up

### 1. Google OAuth (code feature)
`OauthAccount` model + `GOOGLE_*` env vars already exist. To finish Google OAuth login:
- Router: `/auth/google/login` (redirect to Google) + `/auth/google/callback` (exchange code).
- Service: exchange auth code for Google profile, find-or-create `User`, link `OauthAccount` (provider + provider_user_id), then issue the same access/refresh token pair as password login.
- Reuse existing `create_access_token` / `create_refresh_token` / session storage.
- Config: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (already in `.env.example`).
- Handle the case where a Google email matches an existing password user (link vs reject).

### 2. Secrets management (infra)
Blocked on host decision. After picking a host (Fly / Cloud Run / Railway / Render / k8s / etc.), move these out of `.env`:
- JWT private keys (`keys/<kid>/private.pem`)
- `JWT_REFRESH_SECRET`
- `DB_URL`, `REDIS_URL`
- `GOOGLE_CLIENT_SECRET`

Use the host's native secret store (Fly secrets / GCP Secret Manager / AWS SM / Doppler / Vault). See [DEPLOYMENT.md](DEPLOYMENT.md) section 3 for the keys-mounting strategies and section 8 for per-host examples.

### 3. Rotate dev secrets (ops)
Before any deploy — the current `.env` values were exposed during this development session. Rotate:
- `JWT_REFRESH_SECRET` (`python -c "import secrets; print(secrets.token_hex(32))"`)
- `GOOGLE_CLIENT_SECRET` (re-issue in Google Cloud Console)
- RSA keypair (`bash scripts/gen_keys.sh iam-key-prod-1`)

## Known limitations (defer until real ops pain)

- No request-ID middleware → cross-service log correlation is manual.
- Logs are plain text, not JSON → log aggregators do extra parsing.
- `/v1/health` is one endpoint for liveness + readiness; LBs may want split semantics.
- No global rate limit beyond `/auth/login`.
