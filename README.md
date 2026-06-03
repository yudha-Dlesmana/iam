# starter-fastapi — IAM Microservice

Centralized authentication & authorization (IAM) service built with FastAPI.
Issues RS256 JWTs that other microservices verify locally via a JWKS endpoint —
no shared secret, no per-request call back to IAM.

## Features

- **Auth** — login, refresh-token rotation (reuse detection), multi-device sessions, logout / logout-all. Sessions stored in Redis.
- **RBAC** — `User → Role → Permission`. Permissions are namespaced `service.resource.action` (e.g. `iam.user.read`).
- **Asymmetric JWT (RS256)** — IAM signs with a private key; services verify with the public key from JWKS.
- **Key rotation** — multi-key keyset, selected by `kid`; rotate without forcing logout.
- **Token isolation** — `iss` (issuer) and `aud` (audience derived from the user's permission prefixes) claims.
- **Service & permission catalog** — register services, create namespaced permissions, assign to roles.
- **Permission-driven guards** — routes protected by `require_permission("...")`.

## Stack

| Concern | Tech |
|---------|------|
| Framework | FastAPI + Uvicorn |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic |
| Database | MySQL 8 (aiomysql) |
| Sessions / cache | Redis 7 |
| Auth | PyJWT (RS256 access, HS256 refresh), argon2 password hashing |
| Tests | pytest + pytest-asyncio |
| Lint/format | ruff |

## Architecture

Layered: `router → service → repository → model`.

```
src/
  core/        config, database, redis, security (JWT), keys (keyset), logging, cors
  models/      User, Role, Permission, Service, role_permissions, OauthAccount, base
  repositories/ data access per entity
  services/    business logic per entity
  routers/     HTTP endpoints (auth, user, role, permission, service, jwks, health)
  schemas/     pydantic request/response
  lib/         deps (DI + guards), db_errors, pagination
  exceptions/  AppException hierarchy + handlers
scripts/
  seed.py      run all seeders
  seeder/      role, user, service, permission, role_permission
  gen_keys.sh  generate an RSA keypair under keys/<kid>/
alembic/       migrations
tests/         auth, roles, services, permissions
keys/          RSA keypairs per kid (gitignored)
```

### RBAC model

```
User ──role_id──> Role ──role_permissions──> Permission ──service_id──> Service
```

A user inherits permissions from its role. On login the token embeds the role's
permissions and an `aud` list derived from their service prefixes.

## Getting started

### 1. Infrastructure (MySQL + Redis + admin UIs)

```bash
make start          # docker compose up -d
```

Exposes: MySQL `9306`, Adminer `9080`, Redis `9379`, RedisInsight `9540`.

### 2. Environment

```bash
cp .env.example .env
```

Fill in (see **Configuration** below). At minimum: `DB_URL`, `TEST_DB_URL`,
`REDIS_URL`, `JWT_REFRESH_SECRET`.

### 3. Install dependencies

```bash
python -m venv .venv
make install        # pip install -r requirements.txt
```

### 4. Generate JWT signing keys

```bash
make gen-keys       # creates keys/iam-key-1/{private,public}.pem
```

Required — the app signs/verifies access tokens with this keyset. `keys/` is gitignored, so run this on every fresh clone / CI.

### 5. Migrate & seed

```bash
make upgrade        # alembic upgrade head
make seed           # roles, super_admin user, services, permissions, grants
```

### 6. Run

```bash
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
| `JWT_ACTIVE_KID` | key id used to sign (default `iam-key-1`) |
| `JWT_ISSUER` | `iss` claim (default `iam`) |
| `JWT_REFRESH_SECRET` | HS256 secret for refresh tokens |

> **Note:** `.env.example` is out of date — it still lists the old `JWT_ACCESS_SECRET`.
> Access tokens now use the RS256 keyset (`JWT_KEYS_DIR` / `JWT_ACTIVE_KID`); there is
> no `JWT_ACCESS_SECRET`.

## API

Base prefix `/v1`. All non-auth routes require a Bearer access token; mutating
routes require specific permissions.

| Method | Path | Permission |
|--------|------|-----------|
| POST | `/v1/auth/login` | public |
| POST | `/v1/auth/refresh` | refresh cookie |
| POST | `/v1/auth/logout` · `/all-logout` | refresh cookie |
| GET | `/v1/auth/sessions` · `/current-user` | authenticated |
| GET/POST/GET/PATCH/DELETE | `/v1/users` … | `iam.user.read` / `create` / `update` / `delete` |
| GET | `/v1/roles` · `/roles/{id}` | `iam.role.read` |
| POST/PATCH/DELETE | `/v1/roles` … | `iam.role.manage` |
| PUT/POST | `/v1/roles/{id}/permissions` | `iam.role.manage` (set / add) |
| DELETE | `/v1/roles/{id}/permissions/{pid}` | `iam.role.manage` |
| GET/POST/DELETE | `/v1/permissions` … | `iam.permission.read` / `manage` |
| GET/POST/DELETE | `/v1/services` … | `iam.service.read` / `manage` |
| GET | `/v1/health` | public |
| GET | `/.well-known/jwks.json` | public |

### Assigning permissions to a role

`role_id` comes from the URL path, permission ids from the body:

- `PUT  /v1/roles/{id}/permissions` `{ "permission_ids": [1,2] }` — replace the whole set
- `POST /v1/roles/{id}/permissions` `{ "permission_ids": [3] }` — add (keeps existing)
- `DELETE /v1/roles/{id}/permissions/{permission_id}` — remove one

## How services consume IAM tokens

A downstream service verifies tokens locally using IAM's public key (JWKS) — it
never holds a private key. It checks `iss`, `aud` (its own service name), `exp`,
and that `permissions` covers the route, then guards routes with the permission it
owns, e.g. `require_permission("billing.invoice.read")`.

See **[INTEGRATION.md](INTEGRATION.md)** for the full guide: frontend login/refresh
flow, a complete service-side verifier, registering a new service, and running apps
on different domains.

## Testing

```bash
make test-path path=tests/          # all
make test-path path=tests/roles/    # subset
make test-cov                       # with coverage
```

Tests use `TEST_DB_URL` (tables created/dropped per test) and Redis db 15.
`keys/` must exist — run `make gen-keys` first.

## Make targets

| Target | Action |
|--------|--------|
| `make start` / `stop` / `reset` | docker compose up / stop / down -v |
| `make install` | install deps |
| `make run` | run the app |
| `make gen-keys` | generate RSA keypair under `keys/` |
| `make migrate m="msg"` | autogenerate a migration |
| `make upgrade` / `downgrade` | apply / revert migrations |
| `make seed` | seed roles, user, services, permissions |
| `make test-path path=…` / `test-cov` | run tests |

## Roadmap

See [TODO.md](TODO.md) — audit log and secrets management are deferred.
