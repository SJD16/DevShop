#!/bin/bash
set -euxo pipefail

exec > >(tee -a /var/log/devshop-bootstrap.log | logger -t devshop-bootstrap -s 2>/dev/console) 2>&1

echo "===== DevShop EC2 bootstrap started ====="

# --------------------------------------------------
# System packages
# --------------------------------------------------

apt-get update
apt-get install -y ca-certificates curl openssl

# --------------------------------------------------
# Docker
# --------------------------------------------------

install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc

chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update

apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

systemctl enable --now docker

docker --version

# --------------------------------------------------
# DevShop runtime configuration
# --------------------------------------------------

POSTGRES_PASSWORD="$(openssl rand -hex 32)"
JWT_SECRET_KEY="$(openssl rand -hex 32)"

DATABASE_URL="postgresql+psycopg://devshop:${POSTGRES_PASSWORD}@devshop-postgres:5432/devshop"

# --------------------------------------------------
# Docker network
# --------------------------------------------------

docker network create devshop || true

# --------------------------------------------------
# PostgreSQL
# --------------------------------------------------

docker volume create devshop-postgres-data

docker rm -f devshop-postgres 2>/dev/null || true

docker run -d \
    --name devshop-postgres \
    --network devshop \
    --restart unless-stopped \
    -e POSTGRES_USER=devshop \
    -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
    -e POSTGRES_DB=devshop \
    -v devshop-postgres-data:/var/lib/postgresql/data \
    postgres:16

# --------------------------------------------------
# Wait for PostgreSQL
# --------------------------------------------------

echo "Waiting for PostgreSQL..."

for i in {1..60}; do
    if docker exec devshop-postgres \
        pg_isready -U devshop -d devshop >/dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi

    sleep 2
done

docker exec devshop-postgres \
    pg_isready -U devshop -d devshop

# --------------------------------------------------
# DevShop application
# --------------------------------------------------

IMAGE="sjd16/devshop:94010f6"

docker pull "${IMAGE}"

docker rm -f devshop 2>/dev/null || true

docker run -d \
    --name devshop \
    --network devshop \
    --restart unless-stopped \
    -p 8000:8000 \
    -e DATABASE_URL="${DATABASE_URL}" \
    -e JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
    "${IMAGE}"

# --------------------------------------------------
# Wait for application container
# --------------------------------------------------

echo "Waiting for DevShop container..."

for i in {1..60}; do
    if docker inspect -f '{{.State.Running}}' devshop 2>/dev/null | grep -q true; then
        echo "DevShop container is running."
        break
    fi

    sleep 2
done

docker ps

# --------------------------------------------------
# Run database migrations
# --------------------------------------------------

echo "Running Alembic migrations..."

docker exec devshop alembic upgrade head

# --------------------------------------------------
# Application verification
# --------------------------------------------------

echo "Checking DevShop..."

for i in {1..30}; do
    if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1; then
        echo "DevShop HTTP check succeeded."
        break
    fi

    sleep 2
done

curl -fsS http://127.0.0.1:8000/

echo
echo "===== DevShop EC2 bootstrap completed ====="
