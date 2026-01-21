#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
echo "Starting local postgres via docker-compose..."
docker-compose up -d db
echo "Postgres started."
echo "To use it locally, set:"
echo "export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/hotel_project"
