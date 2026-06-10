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

