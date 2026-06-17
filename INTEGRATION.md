# Integrating with the IAM service

How to consume this IAM from your apps: **downstream backend services** that verify tokens, and **frontends** that log users in and call those services.

IAM issues two tokens with different jobs, lifetimes, and trust models:

| Token | Algo | TTL | Who verifies it | Where it lives |
|-------|------|-----|-----------------|----------------|
| **Access** | RS256 (public verify via JWKS) | 15 min | every service, locally | client (in memory) |
| **Refresh** | HS256 (secret, IAM only) | 7 days | IAM only | httpOnly cookie (set by IAM) |

Core idea: services **verify the access token locally** using IAM's public key (JWKS). No shared secret, no per-request callback to IAM. Refresh is strictly between the client and IAM.

---

## Who stores what

Nothing stores the token except the client.

```
             ┌──────────────────┐
             │ CLIENT (browser) │   access token  → in memory
             └─────────┬────────┘   refresh token → httpOnly cookie (set by IAM)
                       │
                       │  Authorization: Bearer <access>   (every API call)
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     ┌─────────┐  ┌─────────┐  ┌──────────┐
     │   IAM   │  │ Billing │  │ Shipping │
     └─────────┘  └─────────┘  └──────────┘
     none of these store tokens — verify per request, then forget.
```

- **Backend services don't store tokens.** They receive one per request, verify it, respond.
- The **client** holds the access token and sends it on every call.
- IAM stores only a **session** in Redis (for refresh), never the access token.

---

## Part 1 — Frontend: logging in and calling services

### Login

```
POST https://iam.com/v1/auth/login
Content-Type: application/json
{ "email": "...", "password": "..." }

-> 200 { "access_token": "<jwt>" }
   + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=None
```

- Store the **access token in memory** (a variable / app state). Avoid `localStorage` — it's readable by XSS.
- The **refresh token is a cookie** you never touch in JS (`HttpOnly`). The browser sends it back to IAM automatically.

### Calling a service

```
GET https://billing.com/v1/invoices
Authorization: Bearer <access token>
```

### Access expired (15 min) — refresh, don't re-login

```
1. billing.com -> 401 (token expired)
2. POST https://iam.com/v1/auth/refresh   (credentials: 'include' — sends the refresh cookie)
   -> 200 { access_token: <new> }         (+ new refresh cookie)
3. retry the original request with the new access token
```

The user only logs in again when the **refresh token expires (7 days)** or is revoked.

### Fetch wrapper (single-flight refresh)

Refresh rotates the token. If many requests get 401 at once and each calls `/refresh`, the older refresh token gets reused → IAM treats it as theft and **revokes every session**. So collapse concurrent refreshes into one ("single-flight"):

```js
// api.js — minimal fetch wrapper, no dependencies
const IAM = 'https://iam.com';
const BILLING = 'https://billing.com';

let accessToken = null;   // kept in memory
let refreshing = null;    // single-flight guard

function refresh() {
  // all concurrent 401s await the same promise
  refreshing ??= fetch(`${IAM}/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',          // sends the refresh cookie
  })
    .then((r) => {
      if (!r.ok) throw new Error('refresh failed');
      return r.json();
    })
    .then((d) => { accessToken = d.access_token; })
    .finally(() => { refreshing = null; });
  return refreshing;
}

export async function apiFetch(path, options = {}) {
  const call = () =>
    fetch(`${BILLING}${path}`, {
      ...options,
      headers: {
        ...options.headers,
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let res = await call();
  if (res.status === 401) {
    try {
      await refresh();               // shared across all waiting requests
    } catch {
      window.location.href = '/login';   // refresh expired / revoked
      throw new Error('session expired');
    }
    res = await call();              // retry once with the new token
  }
  return res;
}
```

### Logout

```
POST https://iam.com/v1/auth/logout       credentials: 'include'   // this device
POST https://iam.com/v1/auth/all-logout   credentials: 'include'   // every device
```

Both clear the refresh cookie. Drop the in-memory access token client-side too.

---

## Part 2 — Backend service: verifying the access token

Your service never talks to IAM per request. It fetches IAM's **public keys once** (JWKS), caches them, and verifies tokens offline.

### What to check on every token

| Claim | Check |
|-------|-------|
| signature | RS256, against the public key for the token's `kid` (from JWKS) |
| `iss` | equals IAM's issuer (`iam`) |
| `aud` | contains **this service's** prefix (e.g. `billing`) |
| `exp` | not expired |
| `permissions` | superset of what the route needs (e.g. `billing.invoice.read`) |

### FastAPI example

```python
# billing/auth.py
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

IAM_JWKS_URL = "https://iam.com/.well-known/jwks.json"
JWT_ISSUER = "iam"            # must match IAM settings.JWT_ISSUER
SERVICE_PREFIX = "billing"    # this service

_jwks = PyJWKClient(IAM_JWKS_URL, cache_keys=True)   # caches keys + refetches on new kid
_bearer = HTTPBearer()


def verify_token(cred: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    token = cred.credentials
    try:
        signing_key = _jwks.get_signing_key_from_jwt(token)   # matches kid -> public key
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            audience=SERVICE_PREFIX,        # aud must contain this service
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}")
    return claims


def require_permission(perm: str):
    def guard(claims: dict = Depends(verify_token)):
        if perm not in claims.get("permissions", []):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "missing permission")
        return claims
    return guard
```

```python
# billing/routers/invoice.py
from fastapi import APIRouter, Depends
from billing.auth import require_permission

router = APIRouter(prefix="/invoices")

@router.get("", dependencies=[Depends(require_permission("billing.invoice.read"))])
async def list_invoices():
    return [...]
```

### Registering a new service in IAM

Before `billing` tokens carry `billing` in `aud` / `permissions`, register it via the admin API (all CRUD endpoints exist — needs the matching `iam.*.manage` permission):

1. Create the service — `POST /v1/services` `{ "name": "billing" }`.
2. Create permissions — `POST /v1/permissions` (`billing.invoice.read`, …).
3. Grant to a role — `POST /v1/roles/{id}/permissions` `{ "permission_ids": [...] }`.

> For first-time/static bootstrap you can also use the seeders
> (`scripts/seeder/service.py`, `permission.py`, `role_permission.py`).

A user whose role holds any `billing.*` permission automatically gets `billing` in their token's `aud` and the relevant `permissions`. One token serves every service the user has access to; each service reads only its own prefix and ignores the rest.

---

## Part 3 — Domains & the refresh cookie

Put the frontend and IAM under the **same parent domain** — FE and IAM on sibling subdomains (e.g. `app.company.com` + `iam.company.com`):

```bash
# IAM .env
COOKIE_DOMAIN=.company.com          # cookie shared first-party across subdomains
FRONTEND_URLs=https://app.company.com
ENV=production                      # cookie flags: HttpOnly; Secure; SameSite=None
```

- The refresh cookie is **first-party** for every `*.company.com` subdomain → immune to browser third-party-cookie blocking.
- `FRONTEND_URLs` must list each FE origin exactly (CORS needs explicit origins, no `*`).
- Every IAM call that needs the cookie must send credentials:

```js
fetch('https://iam.company.com/v1/auth/refresh', { method: 'POST', credentials: 'include' });
// same for /login (to receive the cookie), /logout, /all-logout
```

> Keeping everything under one parent domain avoids the third-party-cookie problems that hit
> unrelated domains (where `SameSite=None` cookies get blocked).

---

## Quick reference

| I want to… | Do this |
|------------|---------|
| Log a user in | `POST /v1/auth/login`, store access in memory, cookie set automatically |
| Call a service | `Authorization: Bearer <access>` |
| Handle 401 | `POST /v1/auth/refresh` (`credentials: 'include'`), retry once |
| Log out | `POST /v1/auth/logout` (this device) / `all-logout` (all) |
| Verify a token in my service | fetch JWKS once, check `iss` / `aud` / `exp` / `permissions` |
| Add my service to IAM | seed service + permissions + role grant |
| Run apps cross-domain | shared parent domain + `COOKIE_DOMAIN=.parent` (recommended) |

### Things that trip people up

- **Backends don't store tokens** — the client does. Backends only verify.
- **One token covers all services** — not one per service. Each service reads its prefix.
- **Permissions are set on the Role, not the User** — a user just picks a role.
- **Refresh only ever goes to IAM** — downstream services have no refresh secret.
- **Concurrent refresh = reuse detection = full logout** — use single-flight refresh.
- **Access tokens are bearer** — not bound to a device; rely on the 15-min TTL + revocation.
```
