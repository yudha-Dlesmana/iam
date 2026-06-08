# Production Hardening — IAM Microservice

Prod **sudah LIVE** (deploy dasar via Cloudflare Tunnel). Dokumen ini = **lapis berikutnya**:
perkuat keamanan, ketahanan, dan operasional. Tidak ada yang nge-block — kerjakan
**berurutan effort-to-impact**, sesuai kebutuhan assurance.

Tiap bagian: **apa**, **kenapa**, **cara**, **effort**.

Urutan saran:
1. Secret → SOPS · 2. Perketat permission key · 3. Backup DB · 4. Rollback deploy ·
5. Rotasi refresh-secret (`kid`) · 6. Revocation per-session · 7. Log JSON + request-id ·
8. Hardening host/network.

---

## 1. Secret management → SOPS (age)  ·  effort: sedang  ·  impact: tinggi

**Apa.** Sekarang `runtime/.env` = plaintext di server. SOPS bikin secret **terenkripsi**,
boleh di-commit, di-decrypt saat deploy.

**Kenapa.** Plaintext di server = siapa pun yang akses disk baca semua secret. Tidak ada
versioning/rollback secret. SOPS: secret di git (terenkripsi), history ada, cuma 1 kunci
(age private) yang dijaga.

**Cara.**

### 1.1 Install (lokal + server)
```bash
brew install sops age                                  # macOS
apt install age && curl -LO <sops-release>.linux.amd64 && install ... /usr/local/bin/sops  # ubuntu
```

### 1.2 Generate age keypair
```bash
age-keygen -o age-key.txt
# Public key: age1xxxx...    (recipient, boleh commit)
# AGE-SECRET-KEY-1...        (PRIVATE — rahasia, cuma di server + backup offline)
```
> ⚠️ Private age key = kunci master. **Hilang → secret tak terdecrypt selamanya. Bocor →
> semua secret terbuka.** Backup di password manager / offline.

### 1.3 `.sops.yaml` (commit)
```yaml
creation_rules:
  - path_regex: secrets/.*\.enc\.env$
    age: age1xxxx...
```

### 1.4 Enkripsi
```bash
sops -e --input-type dotenv --output-type dotenv secrets/prod.env > secrets/prod.enc.env
rm secrets/prod.env
git add .sops.yaml secrets/prod.enc.env
```

### 1.5 Server simpan private key
```bash
mkdir -p ~/.config/sops/age && mv age-key.txt ~/.config/sops/age/keys.txt
```

### 1.6 deploy.sh decrypt (1 baris)
Di `scripts/deploy.sh` preflight, sebelum build:
```bash
sops -d secrets/prod.enc.env > runtime/.env
```
**Compose tidak berubah** — `env_file: runtime/.env` tetap.

### 1.7 `.gitignore`
```
secrets/*.env
!secrets/*.enc.env
age-key.txt
```

---

## 2. Perketat permission private key  ·  effort: cepat  ·  impact: nyata

**Apa.** `deploy.sh` sekarang `chmod -R a+rX runtime/keys` → `private.pem` **world-readable**.

**Kenapa.** User host lain bisa baca private RSA → bisa tandatangani access token palsu.
Pada homelab single-user oke; pada host multi-user / shared = bahaya.

**Cara.** Ganti strategi dari "world-readable" ke "**owned by uid container** (10001), tetap
`0600`". Di `deploy.sh`, ganti baris `chmod`:
```bash
sudo chown -R 10001:10001 runtime/keys
sudo chmod -R 600 runtime/keys/*/private.pem
sudo chmod -R 644 runtime/keys/*/public.pem
```
Container app (uid 10001 dari Dockerfile) baca private; user host lain tidak. Butuh
passwordless sudo untuk user deploy, atau jalankan langkah ini manual sekali.

> Trade-off: butuh `sudo` di deploy. Kalau ga mau sudo → tetap world-readable (cara
> sekarang), terima risikonya di host single-user.

---

## 3. Backup database  ·  effort: cepat  ·  impact: tinggi

**Apa.** Volume `iam_mysql_data` belum di-backup. Disk rusak / `down -v` ga sengaja = semua
user/role/audit hilang.

**Kenapa.** IAM = sumber kebenaran auth. Kehilangan = semua akun ilang. Wajib ada backup.

**Cara.** Cron dump harian:
```bash
# scripts/backup-db.sh
docker exec iam_mysql sh -c \
  'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  | gzip > backups/iam-$(date +%F).sql.gz
find backups -name '*.sql.gz' -mtime +14 -delete   # retensi 14 hari
```
Crontab: `0 2 * * * cd ~/iam && bash scripts/backup-db.sh`.
Restore: `gunzip < backup.sql.gz | docker exec -i iam_mysql mysql -uroot -p... db`.
Bonus: sync `backups/` ke off-site (rclone → R2/S3) biar tahan disk hilang.

---

## 4. Rollback otomatis di deploy.sh  ·  effort: sedang  ·  impact: sedang

**Apa.** `deploy.sh` sekarang `fail` kalau app ga healthy, tapi **biarin** stack setengah
jadi. Tidak balik ke versi sebelumnya.

**Kenapa.** Deploy gagal di prod = downtime sampai diperbaiki manual. Rollback = balik ke
image terakhir yang jalan otomatis.

**Cara.** Sebelum build, tag image lama; kalau healthcheck gagal, retag balik + `up`:
```bash
docker tag iam:prod iam:prev 2>/dev/null || true   # simpan versi lama
# ... build + up + tunggu healthy ...
# di blok fail:
docker tag iam:prev iam:prod && $COMPOSE up -d app
fail "Deploy gagal — rollback ke versi sebelumnya"
```
Plus `trap` on ERR biar rollback jalan walau error di tengah.

---

## 5. Rotasi `JWT_REFRESH_SECRET` ber-`kid`  ·  effort: sedang-tinggi  ·  impact: sedang

**Apa.** Refresh token HS256 ditandatangani **satu** `JWT_REFRESH_SECRET`. Tidak ada
`kid`/rotation (beda dari access token RS256 yang udah ber-kid).

**Kenapa.** Kalau secret bocor → semua refresh token bisa dipalsu. Rotasi sekarang =
invalidasi **semua** sesi sekaligus (mass logout). Dengan kid'd secret, bisa roll mulus:
terbitkan dengan secret baru, tetap verifikasi secret lama sampai expiry.

**Cara.** Di `src/core/security.py`:
- Simpan beberapa secret berversi (`JWT_REFRESH_SECRETS={"v2":"...","v1":"..."}`), `kid`
  aktif di config.
- `create_refresh_token` tandatangani pakai secret aktif + sematkan `kid` di payload.
- `decode_refresh_token` pilih secret by `kid`. Token lama (kid lama) tetap valid sampai
  expiry; secret lama dibuang setelah > refresh TTL (7 hari).

---

## 6. Revocation access-token per-session  ·  effort: sedang  ·  impact: opsional

**Apa.** Revocation sekarang **per-user** (`revoked:user:{id}`). `revoke_session` cuma drop
refresh device itu; access token-nya tetap valid sampai expiry 15 menit.

**Kenapa.** Kalau butuh **kill device tertentu seketika** (mis. logout dari satu HP saja,
instan), per-user ga cukup.

**Cara.** Tambah `sid` (session id) di claim access token; blacklist `revoked:sid:{sid}` di
Redis (TTL = access TTL); cek di `get_current_claims` (gabung ke lookup per-user yang sudah
ada — tetap 1 round-trip). Skip kalau expiry 15 menit dianggap cukup.

---

## 7. Observability: log JSON + request-id  ·  effort: sedang  ·  impact: ops

**Apa.** Log sekarang plain text, tanpa request-id. Korelasi antar-service manual.

**Kenapa.** Aggregator (Loki/ELK) butuh JSON biar query enak. Request-id bikin satu request
bisa dilacak lintas log/service.

**Cara.**
- `src/core/logging.py`: formatter JSON (`python-json-logger` atau custom) saat
  `is_production`.
- Middleware request-id: generate UUID per request (atau pakai `Cf-Ray` dari Cloudflare),
  taruh di contextvar (pola sama `audit_context`), ikutkan di tiap log + header response
  `X-Request-ID`.

---

## 8. Hardening host & network  ·  effort: bervariasi  ·  impact: tinggi

**Apa & cara:**
- **Cloudflare Access** di depan endpoint admin — gate `/v1/users`, `/v1/roles`, dst pakai
  Cloudflare Zero Trust (email/SSO) sebagai lapis kedua sebelum sampai app. Karena trafik
  sudah lewat Cloudflare, tinggal pasang policy. Lapisan ekstra kalau RBAC app jebol.
- **Firewall host** (`ufw`): app sudah tanpa host port (cuma cloudflared yang reach), tapi
  pastikan ga ada port DB/Redis kebuka. `ufw default deny incoming`, allow SSH saja.
- **Auto-update keamanan**: `unattended-upgrades` di Ubuntu.
- **Docker**: `docker scout`/Trivy scan image `iam:prod` untuk CVE; rebuild berkala biar
  base `python:3.11-slim` ke-patch.
- **Fail2ban** untuk SSH.

---

## Ringkasan prioritas

| # | Hardening | Effort | Impact | Kapan |
|---|-----------|--------|--------|-------|
| 1 | SOPS secret | sedang | tinggi | sebelum tim membesar / compliance |
| 2 | Perketat perm key | cepat | nyata | kalau host bukan single-user |
| 3 | Backup DB | cepat | tinggi | **segera** |
| 4 | Rollback deploy | sedang | sedang | kalau deploy makin sering |
| 5 | Refresh-secret kid | sedang-tinggi | sedang | kalau butuh roll tanpa mass-logout |
| 6 | Per-session revoke | sedang | opsional | kalau butuh kill device instan |
| 7 | Log JSON + req-id | sedang | ops | saat mulai pakai aggregator |
| 8 | Host/network | bervariasi | tinggi | bertahap |

**Mulai dari #3 (backup)** — paling cepat, paling sakit kalau ga ada. Lalu #1 (SOPS) + #2
(perm key) buat secret. Sisanya menyusul sesuai kebutuhan.
