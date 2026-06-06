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

### 2. Rotate dev secrets (ops) — URGENT
`.env`/secret values were exposed again during the deploy session (shown in terminal
screenshots): `JWT_REFRESH_SECRET`, `MYSQL_ROOT_PASSWORD=QWE123`, `MYSQL_PASSWORD=qwe123`.
Weak DB passwords + leaked refresh secret. Rotate before treating this as real prod:
- `JWT_REFRESH_SECRET` (`python -c "import secrets; print(secrets.token_hex(32))"`)
- MySQL root + app passwords (strong, random) — update `secrets/production.env` + recreate DB volume
- `GOOGLE_CLIENT_SECRET` (re-issue in Google Cloud Console)
- RSA keypair (`bash scripts/gen_keys.sh iam-key-prod-1`)

### 3. FE auth gate for production cross-domain (frontend / architecture)
The Next.js middleware currently gates routes by reading the IAM-issued
`refresh_token` cookie. This only works in dev because FE (`localhost:9000`) and
IAM (`localhost:9001`) share the host `localhost` (cookies ignore port). In
production with **different domains** (e.g. `app.com` FE, `iam.com` API) the
host-only IAM cookie is never sent to the FE origin, so the middleware always
sees "no cookie" and bounces every user to `/login`. `COOKIE_PATH` is unrelated —
the blocker is the **domain**, not the path. Pick one before launch:
- **Shared parent domain** — serve FE + IAM under `*.company.com` and set
  `COOKIE_DOMAIN=.company.com` so the cookie reaches the FE middleware. Simplest.
- **FE-owned gate** — middleware checks the access token (FE state) or a separate
  non-httpOnly login flag, instead of the IAM refresh cookie.
- **`/me` check** — middleware calls an IAM session endpoint rather than reading
  the cookie directly.

Also revisit CSRF for prod: with `SameSite=None`, `/refresh` is CSRF-triggerable;
impact is limited (new tokens return in the body, unreadable cross-origin) but
consider a CSRF token if tightening. See [INTEGRATION.md](INTEGRATION.md) Part 3.

## Security hardening

Ordered by effort-to-impact. None block dev, but close before a public/high-assurance deploy.

### 4. Fix login timing oracle → user enumeration (quick, real)
`AuthService.login` (`src/services/auth.py:61-66`) only calls `verify_password` when the
user exists. Unknown email returns faster (skips the Argon2 hash), so an attacker can
time-probe which emails are registered — defeating the uniform `"invalid credentials"`
message. Fix: when no user (or no password) is found, run a dummy `verify_password`
against a precomputed throwaway Argon2 hash so both paths spend the same time, then fail.

### 5. CSRF token for `/refresh` under `SameSite=None` (prod)
Confirmed: `_SAMESITE = "none"` in production (`src/routers/auth.py:16`). The refresh
cookie is then sent on cross-site requests, so `/v1/auth/refresh` is CSRF-triggerable.
Impact is limited (rotated tokens return in the body, unreadable cross-origin, and a forged
refresh just rotates the victim's own session) — but add a double-submit CSRF token or an
`Origin`/`Sec-Fetch-Site` check if tightening. Overlaps with #3. See [INTEGRATION.md](INTEGRATION.md) Part 3.

### 6. Global rate limit (defense in depth)
Only `/auth/login` is throttled (`src/services/auth.py`). `/auth/refresh`, password-bearing
and write endpoints have no ceiling. No reverse proxy in front anymore (Caddy removed) —
add the limiter either as app middleware or via **Cloudflare** (WAF / Rate Limiting Rules,
since all traffic now flows through the tunnel) so a single client can't hammer the API or
brute-force refresh tokens.

### 7. Refresh-secret rotation story (single point of failure)
Refresh tokens are HS256 signed by one shared `JWT_REFRESH_SECRET`. If it leaks, every
refresh token is forgeable — and unlike the RS256 access keyset there is no `kid`/rotation
path, so rotating it invalidates all live sessions at once. Decide: either (a) accept it and
lean on rotation #2 + reuse-detection, or (b) move refresh signing to a kid'd keyset (HS256
with versioned secrets, or RS256) so it can roll without a mass logout.

### 8. (Optional) Per-session access-token revocation
Today revocation is per-user (`revoked:user:{id}`, `src/core/revocation.py`) — `revoke_session`
drops only the device's refresh entry, leaving its access token valid until the 15-min expiry.
If instant per-device kill is needed, add a `sid` claim to the access token, blacklist it in
Redis (`revoked:sid:{sid}`, TTL = access TTL), and check it in `get_current_claims` (fold into
the existing per-user lookup — one round-trip). Skip if short TTL is acceptable.

### 9. Cloudflare account + tunnel hardening (ops)
Domain DNS now lives at Cloudflare; the account effectively controls the domain + the
only ingress path. Lock it down:
- Enable **2FA** on the Cloudflare account (and the GitHub account it's OAuth-linked to).
- SSL/TLS mode → **Full (strict)** (not Flexible).
- Internal hop `cloudflared → app:9001` is plain HTTP (safe: same-host docker network).
  Optional upgrade to end-to-end TLS later via a `tls internal` Caddy + tunnel `HTTPS` +
  "No TLS Verify".
- Consider Cloudflare **Access** (Zero Trust) as a login wall in front of IAM admin routes.

## Known limitations (defer until real ops pain)

- No request-ID middleware → cross-service log correlation is manual.
- Logs are plain text, not JSON → log aggregators do extra parsing.
- `/v1/health` is one endpoint for liveness + readiness; LBs may want split semantics.
