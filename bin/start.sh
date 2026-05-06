#!/usr/bin/env bash
set -e

# cd to project root
cd "$(dirname "$0")/.."

# load .env
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# activate .venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Python: $(which python3)"
fi

# 1. start MySQL + Redis
docker compose up -d

# 2. waiting MySQL ready
echo "waiting MySQL ..."
until docker compose exec -T \
    -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
    mysql mysqladmin ping -h 127.0.0.1 -uroot --silent >/dev/null 2>&1; do
    sleep 1
done
echo "mysql is alive"

# 3. waiting Redis ready 
echo "waiting Redis ..."
until docker compose exec -T \
    redis redis-cli ping >/dev/null 2>&1; do
    sleep 1
done
echo "redis is alive"

# 4. apply migration
alembic upgrade head

# 5. seeding
python3 -m scripts.seed

# 6. start app
python3 dev.py