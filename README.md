# IAM Microservice

A centralized **authentication & authorization** service built with FastAPI. It issues
RS256-signed JWT access tokens that other microservices verify **locally** via a JWKS
endpoint — no shared secret, no per-request call back to IAM.

Live in production at **https://iam.smana.web.id** (see [DEPLOYMENT.md](DEPLOYMENT.md)).

## What it does

- **One login for many services.** A user logs in once; the access token carries the role's permissions and an `aud` (audience) list, so every downstream service can authorize requests on its own.
- **Stateless verification.** Services fetch IAM's public keys (JWKS) once and verify tokens offline. IAM holds the private key.
- **Central RBAC.** Roles, permissions, and the service catalog are managed in one place.

## Features
- **Auth** — login, refresh-token rotation with reuse detection, multi-device sessions, logout / logout-all. Sessions in Redis.
- **RBAC** — `User → Role → Permission`, permissions namespaced `service.resource.action` (e.g. `iam.user.read`).
- **Asymmetric JWT (RS256)** — IAM signs with a private key; services verify via JWKS public key.
- **Key rotation** — multi-key keyset selected by `kid`; rotate access keys without forcing logout.
- **Rotatable refresh secret** — HS256 refresh secrets are also `kid`'d, so they roll without a mass logout.
- **Revocation** — per-user and per-session (`sid`) token revocation via Redis.
- **Audit log** — sensitive mutations (role/permission/service CRUD, role grants, user role changes) recorded with actor + IP.
- **Observability** — JSON logs in production with a request-id (from `Cf-Ray` or generated).
- **Permission-driven guards** — routes protected by `require_permission("...")`.

## Strengths & trade-offs

**Strengths**
- No shared secret and no per-request callback to IAM — downstream services scale independently.
- Key + refresh-secret rotation without logging everyone out.
- Defence in depth: argon2 hashing, refresh reuse detection, per-session revocation, audit trail.
- Production-hardened: SOPS-encrypted secrets, DB backups (local + off-site R2), auto-rollback deploy.

**Trade-offs / limitations**
- Revocation checks hit Redis on every authenticated request — gives up the strict
  "zero callback" property if downstream services adopt the same check.
- Access tokens stay valid until their 15-min expiry unless their `sid` is explicitly revoked.
- Refresh-secret rotation is manual (SOPS edit + redeploy) — no runtime rotation endpoint.
- CORS origins are static in env (moving to DB is planned — see [TODO.md](TODO.md)).
- Single `/v1/health` for liveness + readiness; not split for orchestrators yet.
- Google OAuth model exists but the login flow isn't built yet.

## Stack

| Concern | Tech |
|---------|------|
| Framework | FastAPI + Uvicorn |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic |
| Database | MySQL 8 (aiomysql) |
| Sessions / cache | Redis 7 |
| Auth | PyJWT (RS256 access, HS256 refresh), argon2 password hashing |
| Secrets | SOPS + age |
| Tests | pytest + pytest-asyncio |
| Lint/format | ruff |

## Architecture

Layered per entity: `router → service → repository → model`.

```
src/
  core/         config, database, redis, security (JWT), keys (keyset), logging, cors
  models/       User, Role, Permission, Service, role_permissions, OauthAccount, AuditLog
  repositories/ data access per entity
  services/     business logic per entity
  routers/      HTTP endpoints (auth, user, role, permission, service, audit_log, jwks, health)
  schemas/      pydantic request/response
  lib/          deps (DI + guards), audit, revocation, db_errors, pagination
  exceptions/   AppException hierarchy + handlers
scripts/        seed.py, seeder/, gen_keys.sh
alembic/        migrations
tests/          auth, roles, services, permissions
keys/           RSA keypairs per kid (gitignored)
```

### RBAC model

```
User ──role_id──> Role ──role_permissions──> Permission ──service_id──> Service
```

A user inherits permissions from its role. On login the token embeds the role's permissions
and an `aud` list derived from their service prefixes.

## Getting started

```bash
make start          # MySQL 9306, Redis 9379, Adminer 9080, RedisInsight 9540
cp .env.example .env  # fill DB_URL, TEST_DB_URL, REDIS_URL, JWT_REFRESH_SECRETS
python -m venv .venv
make install        # pip install -r requirements-dev.txt
make gen-keys       # creates keys/iam-key-1/{private,public}.pem  (required)
make upgrade        # alembic upgrade head
make seed           # roles, super_admin user, services, permissions, grants
make run            # python main.py
```

Docs at `/docs`. JWKS at `/.well-known/jwks.json`.

## Configuration

Settings load from `.env` (see `src/core/config.py`).

| Var | Purpose |
|-----|---------|
| `ENV` | `development` / anything else = production |
| `HOST`, `PORT` | bind address |
| `FRONTEND_URLs` | CORS origins (comma-separated) |
| `COOKIE_DOMAIN` | refresh-token cookie domain |
| `DB_URL`, `TEST_DB_URL` | async MySQL DSNs |
| `REDIS_URL` | Redis DSN |
| `JWT_KEYS_DIR` | keyset dir (default `keys`) |
| `JWT_ACTIVE_KID` | key id used to sign access tokens (default `iam-key-1`) |
| `JWT_ISSUER` | `iss` claim (default `iam`) |
| `JWT_REFRESH_SECRETS` | JSON dict of versioned HS256 secrets e.g. `{"v1":"<hex>"}` |
| `JWT_REFRESH_ACTIVE_KID` | kid used to sign new refresh tokens (default `v1`) |

## API

Base prefix `/v1`. All non-auth routes need a Bearer access token; mutating routes need
specific permissions.

| Method | Path | Permission |
|--------|------|-----------|
| POST | `/v1/auth/login` | public |
| POST | `/v1/auth/refresh` | refresh cookie |
| POST | `/v1/auth/logout` · `/all-logout` | refresh cookie |
| GET | `/v1/auth/sessions` · `/current-user` | authenticated |
| GET/POST/PATCH/DELETE | `/v1/users` … | `iam.user.read` / `create` / `update` / `delete` |
| GET/POST/PATCH/DELETE | `/v1/roles` … | `iam.role.read` / `manage` |
| PUT/POST/DELETE | `/v1/roles/{id}/permissions` … | `iam.role.manage` |
| GET/POST/DELETE | `/v1/permissions` … | `iam.permission.read` / `manage` |
| GET/POST/DELETE | `/v1/services` … | `iam.service.read` / `manage` |
| GET | `/v1/audit-logs` | `iam.audit.read` |
| GET | `/v1/health` | public |
| GET | `/.well-known/jwks.json` | public |

For consuming IAM tokens from your own services and frontends, see
**[INTEGRATION.md](INTEGRATION.md)**.

## Testing

```bash
make test-path path=tests/          # all
make test-path path=tests/roles/    # subset
make test-cov                       # with coverage
```

Tests use `TEST_DB_URL` (tables created/dropped per test) and Redis db 15. `keys/` must exist
— run `make gen-keys` first.

## Make targets

| Target | Action |
|--------|--------|
| `make start` / `stop` / `reset` | docker compose up / stop / down -v |
| `make install` | install deps (`requirements-dev.txt`) |
| `make run` | run the app |
| `make gen-keys` | generate RSA keypair under `keys/` |
| `make migrate m="msg"` | autogenerate a migration |
| `make upgrade` / `downgrade` | apply / revert migrations |
| `make seed` | seed roles, user, services, permissions |
| `make test-path path=…` / `test-cov` | run tests |

## Docs

- **[INTEGRATION.md](INTEGRATION.md)** — consume IAM from services & frontends.
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — how it's deployed & operated in production.
- **[TODO.md](TODO.md)** — planned features & known limitations.
