# Deployment — IAM Microservice

Deployed & operated on the server (Ubuntu homelab, Docker Compose, Cloudflare Tunnel). Production live at **https://iam.smana.web.id**.


## Arsitektur singkat

All services run via `docker-compose-prod.yml` within the internal `iam_network`:

| Service | Container | Role |
|---------|-----------|------|
| app | `iam_app` | FastAPI, image `iam:prod`, **no host port** |
| mysql | `iam_mysql` | DB (persistent volume) |
| redis | `iam_redis` | sessions + revocation (appendonly) |
| cloudflared | `iam_cloudflared` | Cloudflare Tunnel — the only entry point from the internet |
 
Internet → Cloudflare Tunnel (outbound — no open ports) → `app:9001`.
Public hostname `iam.smana.web.id` → Service **HTTP** `app:9001` (set in the Cloudflare dashboard).


Secrets are managed with SOPS+age. `secrets/prod.enc.env` (encrypted, committed) → Decrypted to `runtime/.env` (gitignored), which every service reads via `env_file`.


---

## 1. First-time setup (sekali per server)

Asumsi: Cloudflare Tunnel sudah dibuat (TUNNEL_TOKEN sudah ada di `prod.enc.env`, public
hostname sudah diarahkan ke `app:9001`).

```bash
# 1. Tools
sudo apt install -y docker.io docker-compose-plugin git age
# + install sops (binary release aquasecurity)

# 2. Clone repo
git clone <repo> ~/iam && cd ~/iam

# 3. Age private key (untuk decrypt SOPS) — simpan di server saja, JANGAN commit
mkdir -p ~/.config/iam
mv age.key ~/.config/iam/age.key           # dari backup offline / password manager
echo 'export SOPS_AGE_KEY_FILE=~/.config/iam/age.key' >> ~/.bashrc && source ~/.bashrc

# 4. RSA signing keys → letak di runtime/keys/<kid>/
bash scripts/gen_keys.sh iam-key-prod-1
mkdir -p runtime/keys && mv keys/iam-key-prod-1 runtime/keys/
#   lalu set permission (lihat §3)
```

Setelah itu deploy pertama: `make deploy`.

---

## 2. Deploy & ops

### Deploy

```bash
make deploy        # jalankan scripts/deploy.sh
make prod-update   # git pull + deploy (untuk update versi baru)
```

`deploy.sh` melakukan, berurutan:
1. **Preflight** — pastikan `secrets/prod.enc.env` + `runtime/keys/` ada.
2. **Decrypt** — `sops -d secrets/prod.enc.env > runtime/.env`.
3. **Build** — tag image lama jadi `iam:prev` (untuk rollback), build `iam:prod`, tag versi
   `iam:<git-describe>`.
4. **Up infra** — start mysql + redis.
5. **Migrate + seed** — `alembic upgrade head && python -m scripts.seed`.
6. **Up app + cloudflared**.
7. **Tunggu healthy** (≤60s). Gagal → **auto-rollback** ke `iam:prev` lalu exit error.

### Cheatsheet

| Perintah | Aksi |
|----------|------|
| `make deploy` | deploy versi sekarang |
| `make prod-update` | git pull + deploy |
| `make prod-restart` | restart app saja |
| `make prod-logs` | tail log semua service |
| `make prod-ps` | status container |
| `make prod-migrate` | migrasi manual |
| `make prod-down` | stop semua |
| `make prod-restore f=<file>` | restore DB dari backup (§4) |

---

## 3. Permission private key (one-time)

Private RSA (`runtime/keys/<kid>/private.pem`) hanya boleh kebaca user container — uid `10001`
(user `app` dari `Dockerfile`). Dijalankan **sekali** setelah generate keys, ulangi kalau
regenerate.

```bash
# chown ke uid container + restrict
sudo chown -R 10001:10001 runtime/keys
sudo find runtime/keys -type d -exec chmod 700 {} \;
sudo find runtime/keys -type f -name '*.pem' -exec chmod 600 {} \;

# verifikasi container baca
docker exec iam_app cat /app/keys/iam-key-prod-1/public.pem | head -1   # → -----BEGIN PUBLIC KEY-----
# verifikasi user host lain TIDAK bisa baca private
sudo -u nobody cat runtime/keys/iam-key-prod-1/private.pem              # → Permission denied
```

> `deploy.sh` tidak `chmod` keys, jadi ownership 10001 tidak ke-override.

---

## 4. Backup & restore DB

### Backup

`scripts/backup-db.sh` dump DB → partisi `/home/yudha/hdd/backup/iam` + off-site ke R2
(`r2:iam-backups/iam`), retensi 14 hari. Manual:

```bash
bash scripts/backup-db.sh
```

### Restore

```bash
make prod-restore f=/home/yudha/hdd/backup/iam/<file>.sql.gz
```

`restore-db.sh` minta konfirmasi `yes`, auto-backup state sekarang dulu (safety net), baru restore.

### Cron (saat ini OFF)

Prasyarat: timezone server = Asia/Jakarta (`sudo timedatectl set-timezone Asia/Jakarta`),
partisi ter-mount, rclone remote `r2` ter-config.

```bash
crontab -e
# minggu jam 2 pagi:
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * 0 /usr/bin/bash /home/yudha/iam/scripts/backup-db.sh >> /home/yudha/hdd/backup/iam/backup.log 2>&1
```

Verifikasi: `cat /home/yudha/hdd/backup/iam/backup.log` + `rclone ls r2:iam-backups/iam`.

---

## 5. Rotasi refresh-secret

`JWT_REFRESH_SECRETS` = dict `{kid: secret}` di `secrets/prod.enc.env`;
`JWT_REFRESH_ACTIVE_KID` = kid penandatangan token baru. Semua kid masih bisa verifikasi →
rotasi tanpa logout massal.

```bash
sops secrets/prod.enc.env
#   JWT_REFRESH_SECRETS={"v1":"<lama>","v2":"<baru>"}   # tambah kid baru
#   JWT_REFRESH_ACTIVE_KID=v2                            # geser active
make prod-update
# tunggu >7 hari (REFRESH_TTL), lalu buang v1.
```

Emergency (secret bocor): buang kid lama langsung (jangan disisakan) → token lama invalid,
logout massal disengaja.

---

## 6. Host & network hardening

Postur: port 22 (SSH), 3306 (MySQL), 6379 (Redis), 9001 (app) **tidak ter-expose** ke
internet (cek: `docker ps` PORTS tanpa `0.0.0.0:`). Akses publik hanya via Cloudflare Tunnel.

### Firewall (ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH          # WAJIB sebelum enable — biar tidak terkunci
sudo ufw enable
sudo ufw status verbose
```

### Fail2ban (SSH brute-force)

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

### Auto security updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades   # pilih Yes
```

### Scan CVE image (Trivy) — rutin bulanan

```bash
trivy image iam:prod --severity HIGH,CRITICAL
```

Tindak lanjut: bump dependency yang `fixed`, `make deploy` untuk patch base `python:3.11-slim`.

---

## 7. Admin FE — CORS & cookie

Admin FE & IAM BE berbagi parent domain `smana.web.id` (FE mis. `admin.smana.web.id`, BE
`iam.smana.web.id`) — meski tunnel terpisah. Satu parent → refresh cookie bisa di-share
**first-party** (tahan blokir third-party cookie).

```bash
sops secrets/prod.enc.env
#    FRONTEND_URLs=https://admin.smana.web.id      ← origin FE (CORS allow-list)
#    COOKIE_DOMAIN=.smana.web.id                   ← cookie dipakai semua subdomain
make prod-update
```

- `FRONTEND_URLs` **harus exact match** scheme+host (`https://`, bukan `http://`). Mismatch →
  preflight lolos tapi request asli kena CORS.
- FE panggil IAM dengan `credentials: 'include'` di semua call auth, pakai prefix `/v1`.

> Cloudflare Access (gate SSO di depan admin FE) opsional — RBAC + argon2 sudah jadi proteksi
> utama.
