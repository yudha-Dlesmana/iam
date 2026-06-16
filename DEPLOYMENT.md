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


> Secrets are managed with SOPS+age. `secrets/prod.enc.env` (encrypted, committed) → Decrypted to `runtime/.env` (gitignored), which every service reads via `env_file`.
---

## Server prerequisites (once per server)

Install **Docker**, **age**, and **sops**.

> SOPS secrets are decrypted with centralized age key at `~/.config/sops/age/keys.txt`
(sops finds it automatically; one file holds one key per project). Restore it from offline backup / password manager — without it, `prod.enc.env` can't be decrypted.
---

## 1. First-time setup

Requires a Cloudflare Tunnel — TUNNEL_TOKEN set in `prod.enc.env`, public hostname points to `app:9001`.

```bash
# 1. Clone the repo
git clone <repo> ~/iam && cd ~/iam

# 2. RSA signing keys → place under runtime/keys/<kid>/
bash scripts/gen_keys.sh iam-key-prod-1
mkdir -p runtime/keys && mv keys/iam-key-prod-1 runtime/keys/

# 3. Key permissions: chown to the container uid + restrict
sudo chown -R 10001:10001 runtime/keys
sudo find runtime/keys -type d -exec chmod 700 {} \;
sudo find runtime/keys -type f -name '*.pem' -exec chmod 600 {} \;
```

First deploy: `make deploy`.

Verify after deploy (container must be running):
```bash
# container can read
docker exec iam_app cat /app/keys/iam-key-prod-1/public.pem | head -1
# other host users CANNOT read the private key
sudo -u nobody cat runtime/keys/iam-key-prod-1/private.pem
```
---

## 2. Deploy & ops

### Deploy

```bash
make deploy        # runs scripts/deploy.sh
make prod-update   # git pull + deploy (for a new version)
```

`deploy.sh` does, in order:
1. **Preflight** — check `secrets/prod.enc.env` + `runtime/keys/` exist.
2. **Decrypt** — `sops -d secrets/prod.enc.env > runtime/.env`.
3. **Build** — tag old image as `iam:prev` (for rollback), build `iam:prod`, tag the version `iam:<git-describe>`.
4. **Up infra** — start mysql + redis.
5. **Migrate + seed** — `alembic upgrade head && python -m scripts.seed`.
6. **Up app + cloudflared**.
7. **Wait healthy** (≤60s). On failure → **auto-rollback** to `iam:prev` then exit error.

### Cheatsheet

| Command | Action |
|----------|------|
| `make deploy` | deploy current version |
| `make prod-update` | git pull + deploy |
| `make prod-restart` | restart app only |
| `make prod-logs` | tail logs of all services |
| `make prod-ps` | container status |
| `make prod-migrate` | run migrations manually |
| `make prod-down` | stop everything |
| `make prod-restore f=<file>` | restore DB from a backup (§3) |
---

## 3. Backup & restore DB

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

## 4. Rotasi refresh-secret

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

## 5. Host & network hardening

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

## 6. Admin FE — CORS & cookie

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
