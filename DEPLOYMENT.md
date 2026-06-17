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

> SOPS secrets are decrypted with centralized age key at `~/.config/sops/age/keys.txt` (sops finds it automatically; one file holds one key per project). Restore it from offline backup / password manager — without it, `prod.enc.env` can't be decrypted.

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

## 2. Backup & restore DB

### Backup

`scripts/backup-db.sh` dumps the DB → partition `/home/yudha/hdd/backup/iam` + off-site ke R2
(`r2:iam-backups/iam`), 14-day retention.

```bash
make  prod-backup
```

### Restore

```bash
make prod-restore f=/home/yudha/hdd/backup/iam/<file>.sql.gz
```

`restore-db.sh` ask for confirmation `yes`, auto-backs up the current state first (safety net), then restores -- a restore **overwrites** the current DB

### Activate Cron (currently OFF)

Prerequisites: server timezone = Asia/Jakarta (`sudo timedatectl set-timezone Asia/Jakarta`),
partition mounted, rclone remote `r2` configured.

```bash
crontab -e
# example: sunday at 2 AM:
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * 0 /usr/bin/bash /home/yudha/iam/scripts/backup-db.sh >> /home/yudha/hdd/backup/iam/backup.log 2>&1
```

Verify: `cat /home/yudha/hdd/backup/iam/backup.log` + `rclone ls r2:iam-backups/iam`.

---

## 3. Refresh-secret rotation

`JWT_REFRESH_SECRETS` = a `{kid: secret}` dict in `secrets/prod.enc.env`;
`JWT_REFRESH_ACTIVE_KID` = the kid (key id) that signs new tokens. All kids can still verify → rotate without mass logout.

```bash
sops secrets/prod.enc.env
#   JWT_REFRESH_SECRETS={"v1":"<old>","v2":"<new>"}   # add the new kid
#   JWT_REFRESH_ACTIVE_KID=v2                         # switch active
make prod-update
# wait >7 days (REFRESH_TTL), then drop v1.
```

**Emergency** (secret leaked): drop the old kid immediately → old tokens become invalid, mass logout is intentional.

---

## 4. Host & network hardening

Posture: ports 22 (SSH), 3306 (MySQL), 6379 (Redis), 9001 (app) are **not exposed** to the internet. Verify:
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"   # PORTS without "0.0.0.0:" → not exposed
```

### Firewall (ufw)

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH          # REQUIRED before enable 
sudo ufw enable
sudo ufw status verbose         # verify -> "Status: active", deny incoming, 22 ALLOW
```

### Fail2ban (SSH brute-force)

```bash
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
sudo systemctl is-active fail2ban
sudo fail2ban-client status sshd      # verify → jail running, shows banned IPs
```

### Auto security updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
sudo systemctl is-active unattended-upgrades
sudo apt-config dump APT::Periodic::Unattended-Upgrade
```

### CVE image scan (Trivy)

Install Trivy (once, via the aquasecurity apt repo):
```bash
sudo apt install -y wget gnupg
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" \
  | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt update && sudo apt install -y trivy
```

Scan:
```bash
trivy image iam:prod --severity HIGH,CRITICAL
```

Follow-up: bump fixed dependencies (in requirements-*.txt), then `make deploy` to rebuild

patch the python:3.11-slim base.

### Access DB via Adminer (on-demand)
```bash
docker run --rm -d --name adminer \
  --network iam_network \
  -p 127.0.0.1:8080:8080 \
  adminer:standalone
```
access via SSH tunnel
```bash
ssh -L 8080:localhost:8080 yudha@homelab
# open http://localhost:8080 
```
stop when done
```bash
docker stop adminer
```
---

## 5. Admin FE — CORS & cookie


Admin FE & IAM BE share the parent domain `smana.web.id` (FE e.g. `admin.smana.web.id`, BE `iam.smana.web.id`) — even though the tunnels are separate. Same parent → the refresh cookie can be shared **first-party** (resistant to third-party cookie blocking).


```bash
sops secrets/prod.enc.env
#    FRONTEND_URLs=https://admin.smana.web.id      ← FE origin (CORS allow-list)
#    COOKIE_DOMAIN=.smana.web.id                   ← cookie used across all subdomainsclear
make prod-update
```

- `FRONTEND_URLs` **must exact-match** scheme+host (https://, not http://). A mismatch → preflight passes but the actual request fails CORS.
- The FE calls IAM with credentials: 'include' on every auth call, using the /v1 prefix.

> Cloudflare Access (an SSO gate in front of the admin FE) is optional — the app's RBAC + argon2 are the primary protection.

---

## 6. Deploy & ops

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
| `make prod-backup` | backup DB now (§2) |
| `make prod-restore f=<file>` | restore DB from a backup (§2) |
