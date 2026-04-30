#!/usr/bin/env bash
set -euo pipefail

curl -fsS "${BACKEND_HEALTH_URL:-http://localhost:8000/health}" >/dev/null

