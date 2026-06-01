# TODO

Deferred work for the IAM microservice. Tracked here so it isn't lost.

## Hardening (before production)

### Secrets management
Deferred — `.env` + gitignored `keys/` is acceptable for development.
Move to a secret manager (Vault / AWS Secrets Manager / etc.) before production:
- JWT private keys (`keys/<kid>/private.pem`)
- `JWT_REFRESH_SECRET`, `DB_URL`, `REDIS_URL`
This is infra work, not code. Keep `.env` and `keys/` out of git (already gitignored).

## Security gaps (review before production)

_All current items delivered. See git history for prior security work._

## OAuth (planned — to implement)

`OauthAccount` model + `GOOGLE_*` env vars already exist. To finish Google OAuth login:
- Router: `/auth/google/login` (redirect to Google) + `/auth/google/callback` (exchange code).
- Service: exchange auth code for Google profile, find-or-create `User`, link `OauthAccount` (provider + provider_user_id), then issue the same access/refresh token pair as password login.
- Reuse existing `create_access_token` / `create_refresh_token` / session storage.
- Config: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (already in `.env.example`).
- Handle the case where a Google email matches an existing password user (link vs reject).

## Code quality / cleanup

_All current items delivered. See git history for prior cleanup work._

