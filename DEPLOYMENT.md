# Deployment Notes — IAM Microservice

## Permission private key (uid container)

**Tujuan.** Private RSA (`runtime/keys/<kid>/private.pem`) cuma kebaca user container —
uid `10001`, user `app` dibuat pada `Dockerfile` (`useradd --uid 10001`) 

**Kapan.** Sekali (one-time) setelah generate keys— tidak perlu tiap deploy.
**Ulangi kalau regenerate keys.**

### Langkah

```bash
# 1. one-time di server: chown ke uid container + restrict
sudo chown -R 10001:10001 runtime/keys
sudo find runtime/keys -type d -exec chmod 700 {} \;
sudo find runtime/keys -type f -name '*.pem' -exec chmod 600 {} \; 

# 2. verifikasi container masih baca (live, tanpa restart)
docker exec iam_app cat /app/keys/iam-key-prod-1/public.pem | head -1
# → -----BEGIN PUBLIC KEY-----

# 3. bukti fresh-start: restart app → re-load keys dengan owner baru
make prod-restart
docker logs --tail 10 iam_app        # tidak ada PermissionError
curl https://iam.<domain>/.well-known/jwks.json   # keys keluar (200)

# 4. bukti hardening: user host lain TIDAK bisa baca private
sudo -u nobody cat runtime/keys/iam-key-prod-1/private.pem
# → Permission denied
```

> `deploy.sh` tidak `chmod` keys (tidak override ownership 10001).

---

## Backup DB — aktifkan cron

Backup DB jalan via `scripts/backup-db.sh` (dump → partisi `/home/yudha/hdd/backup/iam` +
off-site ke R2 `r2:iam-backups/iam`). Penjadwalan pakai cron — **saat ini dimatikan**,
aktifkan kalau perlu.

### Prasyarat
- Server timezone = Asia/Jakarta:
  ```bash
  timedatectl | grep "Time zone"            # cek
  sudo timedatectl set-timezone Asia/Jakarta # kalau masih UTC
  ```
- Partisi `/home/yudha/hdd` ter-mount, rclone remote `r2` ter-config.

### Aktifkan
```bash
crontab -e
```
Tambah (minggu jam 2 malam):
```cron
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * 0 /usr/bin/bash /home/yudha/iam/scripts/backup-db.sh >> /home/yudha/hdd/backup/iam/backup.log 2>&1
```
verify: 
``` bash
crontab -l
```

### Nonaktifkan
```bash
crontab -e        # hapus / kasih '#' di depan baris backup
# atau matikan semua:
crontab -r        # HATI-HATI: hapus SEMUA crontab user
```

### Verifikasi jalan
```bash
cat /home/yudha/hdd/backup/iam/backup.log    # log tiap run
rclone ls r2:iam-backups/iam                  # file ke-upload
```

---

## Rotasi refresh-secret (HS256, ber-`kid`)

Refresh token di assign dengan secret berversi: `JWT_REFRESH_SECRETS` = dict `{kid: secret}`,
`JWT_REFRESH_ACTIVE_KID` = kid yang dipakai **menandatangani** token baru. Semua kid di dict
masih bisa **memverifikasi**. Ini memungkinkan rotasi tanpa logout massal.

**Manual** — server via SOPS (seperti rotasi RS256 key). Secret di
`secrets/prod.enc.env` (terenkripsi).

### Rotasi hygiene
```bash
# 1. generate secret baru
python -c "import secrets; print(secrets.token_hex(32))"

# 2. edit SOPS — tambah kid baru + geser active (server)
sops secrets/prod.enc.env
#    JWT_REFRESH_SECRETS={"v1":"<lama>","v2":"<baru>"}
#    JWT_REFRESH_ACTIVE_KID=v2

# 3. redeploy → token baru pakai v2, token v1 lama TETAP verify (0 logout)
make prod-update

# 4. TUNGGU > 7 hari (REFRESH_TTL) — semua token v1 expire / ke-refresh ke v2

# 5. cleanup — buang v1, redeploy
sops secrets/prod.enc.env
#    JWT_REFRESH_SECRETS={"v2":"<baru>"}
make prod-update
```

### Emergency (secret bocor) — remove linked kid 
```bash
sops secrets/prod.enc.env
#    JWT_REFRESH_SECRETS={"v2":"<baru>"}      ← v1 (bocor) dihapus, TIDAK disisakan
#    JWT_REFRESH_ACTIVE_KID=v2
make prod-update
```
Token v1 (ditandatangani secret bocor) langsung invalid → logout massal **disengaja** (biar
token curian tidak bisa dipakai).

| | Hygiene | Emergency |
|---|---|---|
| kid lama | disisakan 7 hari | dibuang langsung |
| logout user | tidak | ya (disengaja) |

> Aturan: `JWT_REFRESH_ACTIVE_KID` **wajib** salah satu key di `JWT_REFRESH_SECRETS`. Jangan
> tertukar dengan `JWT_ACTIVE_KID` (itu kid access token RS256, keyset terpisah).