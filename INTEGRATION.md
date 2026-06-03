# Integrating with the IAM service

How to consume this IAM from your apps: **downstream backend services** that verify
tokens, and **frontends** that log users in and call those services.

The IAM issues two tokens. They have different jobs, lifetimes, and trust models:

| Token | Algo | TTL | Who verifies it | Where it lives |
|-------|------|-----|-----------------|----------------|
| **Access** | RS256 (public verify via JWKS) | 15 min | every service, locally | client (memory / storage) |
| **Refresh** | HS256 (secret, IAM only) | 7 days | IAM only | httpOnly cookie (set by IAM) |

Core idea: services **verify the access token locally** using IAM's public key (JWKS).
No shared secret, no per-request callback to IAM. Refresh is strictly between the
client and IAM.

---

## Who stores what

Nothing stores the token except the client.

```
┌──────────────────┐
│ CLIENT (browser) │  access token  -> in memory / app state
│                  │  refresh token -> httpOnly cookie (browser-managed, set by IAM)
└────────┬─────────┘
         │  Authorization: Bearer <access>   (every API call)
    ┌────┴────┬──────────────┐
    ▼         ▼              ▼
┌───────┐ ┌────────┐  ┌──────────┐
│  IAM  │ │ Billing│  │ Shipping │   <- none of these store tokens.
└───────┘ └────────┘  └──────────┘      they verify per-request, then forget.
```

- **Backend services do not store tokens.** They receive one per request, verify it, respond.
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

- Store the **access token in memory** (a variable / app state). Avoid `localStorage`
  if you can — it's readable by XSS.
- The **refresh token is a cookie** you never touch in JS (`HttpOnly`). The browser
  sends it back to IAM automatically.

### Calling a service

```
GET https://billing.com/v1/invoices
Authorization: Bearer <access token>
```

### Access expired (15 min) — refresh, don't re-login

```
1. billing.com -> 401 (token expired)
2. fetch('https://iam.com/v1/auth/refresh', {
       method: 'POST',
       credentials: 'include'        // <- REQUIRED: sends the refresh cookie
   })
   -> 200 { access_token: <new> }    // + new refresh cookie
3. retry the original request with the new access token
```

The user only logs in again when the **refresh token expires (7 days)** or is revoked.

### Axios interceptor (single-flight refresh)

Refresh rotates the token. If many requests get 401 at once and each calls
`/refresh`, the older refresh token gets reused → IAM treats it as theft and
**revokes every session**. So collapse concurrent refreshes into one:

```js
import axios from 'axios';

const api = axios.create({ baseURL: 'https://billing.com' });
let accessToken = null;            // kept in memory
let refreshing = null;             // single-flight guard

api.interceptors.request.use((cfg) => {
  if (accessToken) cfg.headers.Authorization = `Bearer ${accessToken}`;
  return cfg;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status !== 401 || original._retried) {
      return Promise.reject(err);
    }
    original._retried = true;

    // one refresh shared by all waiting requests
    refreshing ??= fetch('https://iam.com/v1/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    })
      .then((r) => {
        if (!r.ok) throw new Error('refresh failed');
        return r.json();
      })
      .then((d) => { accessToken = d.access_token; })
      .finally(() => { refreshing = null; });

    try {
      await refreshing;
    } catch {
      // refresh expired / revoked -> back to login
      window.location.href = '/login';
      return Promise.reject(err);
    }
    return api(original);          // retry with new token
  },
);
```

### Logout

```
POST https://iam.com/v1/auth/logout       credentials: 'include'   // this device
POST https://iam.com/v1/auth/all-logout   credentials: 'include'   // every device
```

Both clear the refresh cookie. Drop the in-memory access token client-side too.

---

## Part 2 — Backend service: verifying the access token

Your service never talks to IAM per request. It fetches IAM's **public keys once**
(JWKS), caches them, and verifies tokens offline.

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

_jwks = PyJWKClient(IAM_JWKS_URL, cache_keys=True)   # caches keys + refetches new kid
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

Before `billing` tokens carry `billing` in `aud` / `permissions`, register it in IAM:

1. Seed the service — `scripts/seeder/service.py` (name `billing`).
2. Seed permissions — `scripts/seeder/permission.py` (`billing.invoice.read`, …).
3. Grant to a role — `scripts/seeder/role_permission.py`.

A user whose role holds any `billing.*` permission will automatically get `billing`
in their token's `aud` and the relevant entries in `permissions`. One token serves
every service the user has access to; each service reads only its own prefix and
ignores the rest.

---

## Part 3 — Different domains (chosen topology)

Apps and IAM live on **unrelated domains**:

```
app-a.com      app-b.com      iam.com
```

This works without sharing cookies across domains, because **only IAM reads the
refresh cookie**.

### How the refresh cookie behaves

- IAM sets the refresh cookie **host-only** (`iam.com`). It is **not** shared with
  `app-a.com` or `app-b.com` — and doesn't need to be.
- When `app-a.com` calls `iam.com/v1/auth/refresh` with `credentials: 'include'`,
  the browser attaches the `iam.com` cookie. That's all IAM needs.

### Required configuration

**IAM `.env`:**

```bash
# host-only cookie: leave COOKIE_DOMAIN empty so the cookie binds to iam.com only
COOKIE_DOMAIN=

# every frontend origin that calls IAM (CORS, credentials require explicit origins)
FRONTEND_URLs=https://app-a.com,https://app-b.com

# production => Secure + SameSite=None (set by code when ENV != development)
ENV=production
```

Cookie flags the IAM applies in production (`src/routers/auth.py`):

```
HttpOnly; Secure; SameSite=None; Path=/; Domain=<host-only>
```

- `SameSite=None` + `Secure` is **mandatory** for cross-site (HTTPS required).
- `allow_credentials=True` with an explicit origin list (no `*`) — already configured
  in `src/core/cors.py`.

**Frontend:** every call to IAM that needs the cookie must send credentials:

```js
fetch('https://iam.com/v1/auth/refresh', { method: 'POST', credentials: 'include' });
// same for /login (to receive the cookie), /logout, /all-logout
```

### Trade-off you are accepting

`SameSite=None` cookies are **third-party** cookies in this topology. Modern browsers
(Chrome's third-party cookie phase-out) increasingly block them, which can make
`/refresh` fail silently.

If that becomes a problem, the robust fix is to move everything under one parent
domain (`app-a.company.com`, `iam.company.com`) and set `COOKIE_DOMAIN=.company.com`
— then the refresh cookie is first-party and immune to the block. Until then,
host-only + `SameSite=None` is the supported cross-domain setup.

---

## Quick reference

| I want to… | Do this |
|------------|---------|
| Log a user in | `POST /v1/auth/login`, store access in memory, cookie set automatically |
| Call a service | `Authorization: Bearer <access>` |
| Handle 401 | `POST /v1/auth/refresh` (`credentials: include`), retry once |
| Log out | `POST /v1/auth/logout` (this device) / `all-logout` (all) |
| Verify a token in my service | fetch JWKS once, check `iss` / `aud` / `exp` / `permissions` |
| Add my service to IAM | seed service + permissions + role grant |
| Run apps on different domains | `COOKIE_DOMAIN=`, list origins in `FRONTEND_URLs`, send `credentials` |

### Things that trip people up

- **Backends don't store tokens** — the client does. Backends only verify.
- **One token covers all services** — not one token per service. Each service reads its prefix.
- **Permissions are set on the Role, not the User** — a user just picks a role.
- **Refresh only ever goes to IAM** — downstream services have no refresh secret.
- **Concurrent refresh = reuse detection = full logout** — use single-flight refresh.
- **Access tokens are bearer** — not bound to a device; rely on the 15-min TTL and revocation.
