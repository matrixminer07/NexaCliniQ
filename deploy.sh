#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Update secrets before production use."
fi

get_env_value() {
  local key="$1"
  local line
  line=$(grep -E "^${key}=" .env | tail -n 1 || true)
  echo "${line#*=}"
}

validate_secret() {
  local key="$1"
  local value
  value=$(get_env_value "$key")

  if [ -z "$value" ]; then
    echo "Missing required ${key} in .env"
    exit 1
  fi

  if [ "${#value}" -lt 32 ]; then
    echo "${key} must be at least 32 characters for production deployments"
    exit 1
  fi

  case "$value" in
    *your-secret*|*change-me*|*replace-with*)
      echo "${key} appears to be a placeholder. Set a strong random value before deploying."
      exit 1
      ;;
  esac
}

validate_secret "SECRET_KEY"
validate_secret "JWT_SECRET_KEY"
validate_secret "AUTH_JWT_SECRET"

echo "Running: docker compose up --build -d"
docker compose up --build -d

echo "Services status:"
docker compose ps

echo "Backend health check:"
if curl -fsS http://localhost/health >/dev/null; then
  echo "HTTP 200"
else
  echo "Health endpoint not reachable yet. Check logs with: docker compose logs -f backend nginx"
fi
