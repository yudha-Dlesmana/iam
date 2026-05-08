#!/usr/bin/env bash
set -e

#
if ! docker info > /dev/null 2>&1; then
    echo "starting Docker ..."
    open -a Docker --background
    until docker info > /dev/null 2>&1; do sleep 1; done
    echo "docker ready"
fi

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

# 3. ensure databases + user
echo "ensuring database ..."
docker compose exec -T \
    -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
    mysql mysql -uroot <<SQL
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}_test\`;
GRANT ALL ON \`${DB_NAME}\`.* TO '${DB_USER}'@'%';
GRANT ALL ON \`${DB_NAME}_test\`.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
echo "database ready"

# 4. waiting Redis ready 
echo "waiting Redis ..."
until docker compose exec -T \
    redis redis-cli ping >/dev/null 2>&1; do
    sleep 1
done
echo "redis is alive"

# 5. apply migration
alembic upgrade head

ALEMBIC_DB_URL="$TEST_DB_URL" alembic upgrade head

# 6. seeding
python3 -m scripts.seed

# 7. start app
python3 dev.py