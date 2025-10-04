#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../services/compose"
export $(grep -v '^#' .env.ai.example | xargs -d '\n' -I{} echo {} | xargs -0 echo >/dev/null 2>&1 || true)
docker compose -f docker-compose.ai.yml --env-file .env.ai up -d
echo "Scout:   http://localhost:8001/v1"
echo "Analyst: http://localhost:8002/v1"
echo "Judge:   http://localhost:8003/v1"
