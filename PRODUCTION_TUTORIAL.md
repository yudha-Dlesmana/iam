# Production Tutorial — IAM Microservice

Panduan langkah demi langkah untuk membawa project ini ke production di **Ubuntu server +
domain + Cloudflare Tunnel**. Tiap langkah dijelaskan **kenapa**-nya supaya kamu paham,
bukan cuma copy-paste.

Bagian fix kode keamanan (timing oracle, global rate limit, CSRF `/refresh`) **sudah masuk
ke project**. Sisa: **config & secret** (B) → **deploy** (C).

> Catatan: B & C dijalankan di server. Setelah selesai, jalankan test (langkah akhir) untuk
> memastikan tidak ada yang rusak.

---

## Bagian B — Config & secret production

### B1. Generate RSA keypair production

App **gagal start** kalau `keys/<kid>/` tidak ada (`src/core/keys.py` raise `RuntimeError`).
Buat keypair khusus prod (jangan pakai key dev):

```bash
bash scripts/gen_keys.sh iam-key-prod-1
```

Lalu set di `.env`: `JWT_ACTIVE_KID=iam-key-prod-1`.

**Kenapa kid baru?** Access token RS256 punya `kid` di header. Downstream verifikasi via
JWKS. Key dev mungkin sudah terekspos saat development → jangan dipakai di prod.

### B2. Rotate semua secret dev (WAJIB sebelum deploy)

Secret di `.env` dev sudah terekspos selama pengembangan. Ganti semua:

```bash
# JWT refresh secret baru
python -c "import secrets; print(secrets.token_hex(32))"
```

- `JWT_REFRESH_SECRET` → pakai hasil di atas.
- `GOOGLE_CLIENT_SECRET` → re-issue di Google Cloud Console.
- Password MySQL (`qwe123` / root `QWE123`) → ganti dengan password kuat, update `DB_URL`.

**Kenapa penting:** kalau `JWT_REFRESH_SECRET` bocor, **semua** refresh token bisa
dipalsukan (HS256, satu secret). Tidak ada `kid`/rotation untuk refresh, jadi kebersihan
secret ini krusial.

### B3. Isi `.env` production

File `.env` hanya ada di server, **jangan commit**. Isi:

```
ENV=production
HOST=0.0.0.0
PORT=9001
FRONTEND_URLs=https://app.domainkamu.com
COOKIE_DOMAIN=.domainkamu.com        # supaya cookie sampai ke FE (parent domain sama)
FORWARDED_ALLOW_IPS=127.0.0.1        # cuma percaya cloudflared di localhost
DB_URL=mysql+aiomysql://fastapi:<pw-kuat>@db:3306/iam_db
REDIS_URL=redis://redis:6379
JWT_ACTIVE_KID=iam-key-prod-1
JWT_REFRESH_SECRET=<hasil-rotate>
GOOGLE_CLIENT_SECRET=<hasil-rotate>
GOOGLE_REDIRECT_URI=https://iam.domainkamu.com/api/v1/oauth/google/callback
```

**Yang otomatis benar saat `ENV=production`:** cookie `Secure`, header HSTS, dan
`SameSite=None` sudah auto-aktif (`src/routers/auth.py`, `src/core/security_headers.py`).
Cloudflare yang terminasi TLS di edge, jadi cookie HTTPS valid walau app di belakang
HTTP-localhost.

### B4. Matikan `/docs` di production (opsional, disarankan)

`src/app.py` selalu expose `/docs` (root redirect ke sana). Di prod, sembunyikan supaya
struktur API tidak bocor:

```python
_docs = None if settings.is_production else "/docs"
app = FastAPI(
    lifespan=lifespan,
    docs_url=_docs,
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
```

Dan guard redirect `/` supaya tidak ke `/docs` saat prod.

---

## Bagian C — Deploy: Docker + Cloudflare Tunnel di Ubuntu

### C1. Buat ulang Dockerfile

Dockerfile sebelumnya dihapus (commit `085005a`). Buat lagi di root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependency dulu (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./
COPY scripts/ ./scripts/

# JANGAN copy keys/ atau .env — itu di-mount/inject saat runtime.

EXPOSE 9001
CMD ["python", "main.py"]
```

**Kenapa keys & .env tidak di-bake?** Image bisa ter-push ke registry / ke-share. Secret
di dalam image = kebocoran permanen. Mount saat runtime saja.

### C2. Compose production

Buat `docker-compose-prod.yml`:

```yaml
services:
  app:
    build: .
    env_file: .env
    volumes:
      - ./keys:/app/keys:ro          # keypair di-mount read-only
    ports:
      - "127.0.0.1:9001:9001"        # HANYA localhost — publik tidak bisa akses langsung
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped
    # tidak ada 'ports:' — hanya jaringan internal compose

  redis:
    image: redis:7
    restart: unless-stopped
    # tidak ada 'ports:'

volumes:
  mysql_data:
```

**Kunci keamanan:** `127.0.0.1:9001:9001`. App tidak terbuka ke internet. DB & Redis tanpa
`ports:` sama sekali — hanya dipanggil antar-container. Satu-satunya pintu masuk publik =
Cloudflare Tunnel (C3).

Jalankan:

```bash
docker compose -f docker-compose-prod.yml up -d --build
```

### C3. Cloudflare Tunnel

Install & sambungkan tunnel di host Ubuntu:

```bash
# install cloudflared (Debian/Ubuntu)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

cloudflared tunnel login                    # buka browser, pilih domain kamu
cloudflared tunnel create iam               # buat tunnel bernama 'iam'
```

Buat config `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL-ID-dari-create>
credentials-file: /home/<user>/.cloudflared/<TUNNEL-ID>.json

ingress:
  - hostname: iam.domainkamu.com
    service: http://127.0.0.1:9001
  - service: http_status:404
```

Routing DNS + jalankan sebagai service:

```bash
cloudflared tunnel route dns iam iam.domainkamu.com
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

**Alur trafik:** user → `https://iam.domainkamu.com` → Cloudflare (terminasi TLS) →
tunnel → `http://127.0.0.1:9001` (app). IP asli klien sampai via `X-Forwarded-For`, dan
`_client_ip` di kode sudah membacanya — jadi rate-limit & audit log dapat IP benar. Karena
app di-bind localhost, header XFF tidak bisa dipalsukan dari luar.

### C4. Migrasi & seed database (sekali saat pertama)

```bash
docker compose -f docker-compose-prod.yml exec app alembic upgrade head
docker compose -f docker-compose-prod.yml exec app python -m scripts.seed
```

`upgrade` bikin tabel; `seed` isi role, super_admin, service, permission, grant.

### C5. Ganti password super_admin default

Seeder hardcode `super_admin@starter.com` / `!Qwer123` (`scripts/seeder/user.py`). Ini
**default publik** — wajib ganti. Login pertama kali, lalu ganti password lewat endpoint
user. Jangan biarkan default.

---

## Verifikasi

### Sebelum deploy (lokal/dev)

```bash
make install
make gen-keys            # bikin keys/iam-key-1 untuk dev
make upgrade
pip install ruff && ruff check src tests     # lint sama seperti CI
pytest tests/ -v                              # semua harus hijau
```

### Test untuk fix keamanan yang sudah masuk (tulis sendiri biar paham)

1. **Timing oracle** — test bahwa `verify_password` tetap dipanggil walau email tidak ada
   (mock/spy `verify_password`, login dengan email asing, assert dipanggil).
2. **Global rate limit** — kirim request > `GLOBAL_RATE_LIMIT` dari satu IP → harap `429` +
   header `Retry-After`. Pastikan `/v1/health` tidak kena.
3. **CSRF refresh** — `POST /v1/auth/refresh` dengan header `Origin` lintas-situs → `403`;
   dengan `Origin` yang ada di `FRONTEND_URLs` → sukses rotate.

### Smoke test production (setelah tunnel jalan)

```bash
curl https://iam.domainkamu.com/health
# → {"status":"ok", "database":{"status":"ok"}, "redis":{"status":"ok"}, ...}

curl https://iam.domainkamu.com/.well-known/jwks.json
# → JSON berisi kid "iam-key-prod-1"

curl -i https://iam.domainkamu.com/docs
# → 404 (kalau B4 diterapkan)
```

- Login → cek response punya cookie `Secure; HttpOnly; SameSite=None` dan header
  `Strict-Transport-Security`.
- Dari mesin lain, coba akses port app langsung (mis. `http://<ip-server>:9001`) → harus
  **gagal/timeout** (hanya tunnel yang boleh).

---

## Di luar scope (catat di TODO.md, kerjakan nanti)

- #4 strategi penuh FE lintas-domain di luar `COOKIE_DOMAIN` (kerjaan sisi FE).
- #8 rotasi `JWT_REFRESH_SECRET` ber-`kid` (sekarang satu secret HS256; andalkan rotasi
  manual + reuse-detection).
- #9 revocation access-token per-session.
- #1 Google OAuth, log JSON / request-id middleware.

---

## Ringkasan urutan eksekusi

```
(Bagian A — fix kode keamanan — sudah masuk project)
   ↓
B1 gen prod keys  →  B2 rotate secret  →  B3 .env prod  →  B4 matikan docs
   ↓
C1 Dockerfile  →  C2 compose up  →  C3 cloudflared tunnel  →  C4 migrate+seed  →  C5 ganti admin pw
   ↓
Verifikasi smoke test
```
