# TODO

Deferred work for the IAM microservice. Tracked here so it isn't lost.

## Features

### Single-session for super_admin (hybrid)
Not implemented. Current design is intentionally **multi-device**: sessions are
stored per device in the Redis hash `sessions:{user_id}` (see `core/security.py`),
and `/auth/sessions` lists all active devices. One account can be logged in on
many devices at once.

Goal: **super_admin = single active session** (anti account-sharing on the most
privileged account); **all other roles stay multi-device** (convenient for CMS use).

Plan:
- In `AuthService.login`, before `store_session`, if the user's role requires
  single session, call `revoke_user(redis, user.id)` to drop existing sessions
  (newest-login-wins policy — avoids lockout).
- Decide how to flag it:
  - hardcode `if user.role_name == "super_admin"` (simplest, fragile if renamed), or
  - add a `Role.single_session: bool` column (flexible, needs a migration).
- Caveat: `revoke_user` only clears the refresh session in Redis. The old access
  token (RS256, 15 min) stays valid until it expires — the old device loses the
  ability to refresh but keeps access for up to 15 min. Instant kill needs access
  token revocation (see Security gaps).
- Note on "per service": sessions are tracked per *user*, not per user+service.
  The same access token works across every service in its `aud`. If single-session
  must be scoped per service, the session key would need the service/audience
  (e.g. `sessions:{user_id}:{service}`) and tokens issued per service.

## Hardening (before production)

### Audit log
Deferred — only one super_admin for now, so attribution is unambiguous.
Implement when there are multiple admins or before going to production.

Design:
- Table `audit_logs`: `actor_id`, `action`, `target_type`, `target_id`, `meta` (JSON, **not** `metadata` — reserved by SQLAlchemy), `ip`, `created_at`.
- Carry `actor_id` + `ip` via `contextvars` (set `actor_id` in `get_current_claims`, set `ip` in middleware) so service signatures stay clean.
- Record only sensitive mutations: role create/update/delete, role set/add/remove permission, service create/delete, permission create/delete, user role change.
- Persist to DB (permanent evidence) **and** mirror to the app logger.
- Optional `GET /v1/audit-logs` guarded by `iam.audit.read`.

### Secrets management
Deferred — `.env` + gitignored `keys/` is acceptable for development.
Move to a secret manager (Vault / AWS Secrets Manager / etc.) before production:
- JWT private keys (`keys/<kid>/private.pem`)
- `JWT_REFRESH_SECRET`, `DB_URL`, `REDIS_URL`
This is infra work, not code. Keep `.env` and `keys/` out of git (already gitignored).

## Security gaps (review before production)

- **Access token revocation** — RS256 access tokens can't be revoked until they expire (15 min). A banned user keeps access until then. If instant revocation is needed, blacklist `jti` in Redis and check it on each request (trades off the "no callback to IAM" property).
- **Pagination cap** — list endpoints take `limit` with no upper bound; a caller can request a huge page. Cap at e.g. 100.
- **Security headers / CORS** — add HSTS, X-Frame-Options, etc. via middleware; tighten CORS origins for production.

## OAuth (planned — to implement)

`OauthAccount` model + `GOOGLE_*` env vars already exist. To finish Google OAuth login:
- Router: `/auth/google/login` (redirect to Google) + `/auth/google/callback` (exchange code).
- Service: exchange auth code for Google profile, find-or-create `User`, link `OauthAccount` (provider + provider_user_id), then issue the same access/refresh token pair as password login.
- Reuse existing `create_access_token` / `create_refresh_token` / session storage.
- Config: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (already in `.env.example`).
- Handle the case where a Google email matches an existing password user (link vs reject).

## Code quality / cleanup

- **Test coverage gaps**: `aud` derivation (`_audience_from`), `decode_access_token` rejecting bad `iss`/`aud`, user CRUD, JWKS endpoint, key rotation, consumer-side verify.
- `keys.py` uses `lru_cache` — key rotation needs an app restart to pick up new keys (fine for scheduled rotation; note it).

