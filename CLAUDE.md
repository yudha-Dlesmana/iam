# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Centralized IAM (auth + RBAC) microservice. FastAPI issues RS256 JWTs; downstream services verify locally via JWKS — no shared secret, no per-request callback. Refresh tokens are HS256 and rotated; sessions live in Redis.

## Commands

All targets run through the `.venv` interpreter — activate or use `make` directly. Compose targets bring up local MySQL (`9306`), Redis (`9379`), Adminer (`9080`), RedisInsight (`9540`).

```bash
make start            # docker compose up -d  (mysql + redis + UIs)
make stop / reset     # stop / down -v
make install          # pip install -r requirements.txt
make gen-keys         # scripts/gen_keys.sh iam-key-1  (REQUIRED before run/test)
make upgrade          # alembic upgrade head
make seed             # python -m scripts.seed
make run              # python main.py  (uvicorn, reload if ENV=development)
make migrate m="msg"  # alembic revision --autogenerate

make test-path path=tests/                      # full suite
make test-path path=tests/auth/test_login.py    # single file
make test-path path=tests/auth/test_login.py::test_name  # single test
make test-cov         # pytest --cov=src --cov-report=term-missing

ruff check src tests  # lint (matches CI)
```

CI (`.github/workflows/ci.yml`) runs `ruff check src tests` then `pytest tests/ -v` against MySQL 8 + Redis 7 service containers. Triggers on `main` and `development-*` branches.

## Pre-run requirements

- `.env` must define `DB_URL`, `TEST_DB_URL`, `REDIS_URL`, `JWT_REFRESH_SECRET`. `.env.example` is stale — it lists a removed `JWT_ACCESS_SECRET`; access tokens now use RS256 keyset only.
- `keys/<kid>/{private,public}.pem` must exist before app start or tests — `src/core/keys.py` raises `RuntimeError` at module load if `JWT_ACTIVE_KID` not present. Run `make gen-keys` on every fresh clone / CI.
- Tests require a reachable `TEST_DB_URL` MySQL (tables `create_all`/`drop_all` per test via `tests/conftest.py`) and Redis (uses db 15, flushed around each test).

## Architecture

Layered per entity: `router → service → repository → model`. DI wires layers through `src/lib/deps.py` using `Annotated[..., Depends(...)]` aliases (`DbSession`, `RedisClient`, `*ServiceDep`).

```
src/
  core/         config, database (async engine + session), redis, security (JWT + sessions),
                keys (lru_cached keyset loader), logging, cors
  models/       SQLAlchemy 2 async ORM. UUID PK on User. TimestampMixin = created_at/updated_at.
  repositories/ data access only. Use selectinload for role+permissions eager loads.
  services/     business logic. Catch IntegrityError → translate via lib/db_errors to AppException.
  routers/      HTTP. Mount under /v1 in src/routers/api.py. JWKS at /.well-known/jwks.json (root).
  schemas/      pydantic request/response (validators in schemas/validators.py).
  lib/deps.py   DI factories + `require_permission(...)` / `require_role(...)` guards.
  exceptions/   AppException hierarchy → JSONResponse via handlers.py (registered in app.py).
alembic/        migrations. env.py reads ALEMBIC_DB_URL or settings.DB_URL.
scripts/seeder/ roles, super_admin user, services, permissions, role_permission grants.
keys/<kid>/     RSA keypairs (gitignored). kid = directory name.
```

### Auth + JWT flow

- `src/core/security.py` — access token RS256 (15min, signed with `active_private_key()`, `kid` in JWT header), refresh HS256 (7d, `JWT_REFRESH_SECRET`).
- Access claims include `sub`, `iss`, `aud` (derived from the user's permission service prefixes — `_audience_from`), `role`, `permissions`.
- Refresh rotation uses an atomic Redis Lua script (`_ROTATE_LUA`): returns `OK` / `MISSING` / `REUSE`. On `REUSE` `AuthService.refresh` revokes the entire user's sessions (reuse-detection).
- Sessions stored as Redis hash `sessions:{user_id}` with `device` field; TTL = refresh TTL. One device = one entry. `logout` deletes one device, `all-logout` deletes the whole hash.
- `src/core/keys.py` loads all kids under `JWT_KEYS_DIR` once (lru_cache). Rotation = add a new dir, switch `JWT_ACTIVE_KID`; old kids stay verifiable. JWKS endpoint (`src/routers/jwks.py`) exposes every public key by kid. New kids on disk are NOT picked up until the app restarts or `keys.reload()` is called — production rotation is intended to be a scheduled deploy, so this is by design.

### RBAC

`User ──role_id──> Role ──role_permissions──> Permission ──service_id──> Service`. Permission names are namespaced `service.resource.action` (e.g. `iam.user.read`). Guards: `require_permission("iam.role.manage")` as a `dependencies=[...]` entry on routes. `claims["permissions"]` must be a superset of required.

Roles can opt into single-session mode via `Role.single_session` (bool column, default false; super_admin seeded as true). When set, `AuthService.login` calls `revoke_user` before issuing a new refresh session — newest-login-wins. Caveat: only the refresh session is dropped; the old device's existing access token stays valid until its 15-min expiry.

### Access token revocation

`src/core/revocation.py` stores a per-user "revoked at" epoch in Redis (`revoked:user:{id}`, TTL = access TTL + buffer). `get_current_claims` rejects any token whose `iat <= revoked_at`. Tradeoff: every authenticated request now hits Redis — gives up the strict "no callback to IAM" property for downstream services if they adopt the same check. Marker is bumped by `UserService.revoke_tokens` (also drops refresh sessions) and `UserService.delete`. `POST /v1/users/{id}/revoke-tokens` is gated by `iam.user.update`. Both write `user.revoke_tokens` / `user.delete` audit entries.

### Audit log

Sensitive mutations (role/service/permission CRUD, role-permission grants, user role changes) write an `AuditLog` row in the same DB transaction. `actor_id` + `ip` are carried via `contextvars` (`src/core/audit_context.py`) — `get_current_claims` sets the actor, `AuditContextMiddleware` sets the IP. Services call `src/lib/audit.record(session, action, target_type, target_id, meta)` after a successful mutation; the row participates in the request's transaction, so failed mutations leave no audit trace. `GET /v1/audit-logs` (guarded by `iam.audit.read`) lists rows newest-first, filterable by action / target_type / actor_id.

### Error handling contract

Services raise subclasses of `AppException` (`NotFoundError` 404, `ConflictError` 409, `ValidationError` 422, `UnauthorizedError` 401, `ForbiddenError` 403). Don't `raise HTTPException` in services. `register_exception_handlers` in `src/exceptions/handlers.py` maps them to `{"message": ...}` JSON. `RequestValidationError` is reformatted into `{"message": "validation error", "errors": ["field: msg", ...]}`. Translate DB errors via `lib/db_errors.is_unique_violation` / `is_fk_violation` / `is_check_violation(e, name)` — these handle both MySQL error codes and class-name strings.

### DB sessions

`get_db` commits on success / rolls back on exception per request. Repositories call `session.flush()` (not commit). Don't commit inside services/repos — let the request boundary do it. Tests override `get_db` and `get_redis` via `app.dependency_overrides` in `tests/conftest.py`.

## Conventions

- Python 3.11. Async everywhere (SQLAlchemy async, aiomysql, redis.asyncio, httpx in tests).
- New entity = add model, repository, service, schema, router; register router in `src/routers/api.py`; add migration; add seeder if static data.
- New permission = seed it via `scripts/seeder/permission.py` + grant in `role_permission.py`; reference name string in `require_permission(...)`.
- New JWT key = `scripts/gen_keys.sh <new-kid>`, deploy, then flip `JWT_ACTIVE_KID`. Old tokens keep verifying until expiry.
