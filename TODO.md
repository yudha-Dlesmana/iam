# TODO

Backlog fitur & bug untuk IAM. Tambah item baru di section yang sesuai.

## Features


### 1. Separate health check: liveness and readiness
- `/health/live` → app process is up.
- `/health/ready` → DB + Redis reachable.

Used for orchestrator (Kubernetes / LB): if DB goes down, readiness fails but liveness
stays OK (app isn't restarted needlessly). 
Not urgent for the current Docker + Cloudflare Tunnel setup.


### 2. Account activation via email
New users start with `email_verified = false` and verify via an email link.

- Add `email_verified` column (bool, default `false`) to `users` — needs an Alembic migration.
- On create: email a verification link with a token (Redis, TTL ~24h).
- `POST /v1/auth/verify-email` → verify token → set `email_verified = true`.
- Reject login while `email_verified = false`. Google OAuth users (#3) are verified right away.

Needs email infra (SMTP config + async send helper), reused later for password reset.


### 3. Google OAuth login
Login with a Google account

- Router: `GET /v1/auth/google/login` (redirect to Google) + `GET /v1/auth/google/callback`
- Service: exchange code → profile, find-or-create `User`, link to `OauthAccount`
  (provider + provider_user_id), then issue access + refresh tokens.
- Edge case: if a goole email matches an existing user, list the google account to it
  (require `email_verified = true).

### 4. CORS origins from DB
Store allowed origins in the database

Architecture:
- Portfolio projects live on `*.smana.web.id` subdomains.
- `COOKIE_DOMAIN=.smana.web.id` → refresh cookie is first-party across subdomains.
- Load origins from DB once at startup (add project = insert row + restart).

To build:
- Add `origins` column to `services` (+ Alembic migration).
- Make `src/core/cors.py` read the allow-list form DB
- Service seeder can set origins

## Bugs

_(belum ada)_
