#!/usr/bin/env bash
set -euo pipefail

git pull origin main
./ops/scripts/preflight.sh
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
sleep 10
./ops/scripts/healthcheck.sh
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend
./ops/scripts/healthcheck.sh

