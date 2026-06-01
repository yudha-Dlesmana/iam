# TODO

Deferred work for the IAM microservice. Tracked here so it isn't lost.

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

## Done
- RS256 access tokens + JWKS endpoint
- Multi-key keyset + rotation by `kid`
- `iss` / `aud` claims (aud derived from permission prefixes)
- services table + namespaced permissions (`service.resource.action`)
- service / permission CRUD, role permission set/add/remove
- permission-driven guards (`require_permission`)
- app logger + 500 handler
- 35 tests passing
