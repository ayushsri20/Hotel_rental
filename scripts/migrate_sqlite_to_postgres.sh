#!/usr/bin/env bash
set -euo pipefail
# Helper to safely migrate data from the local SQLite DB to a Postgres instance
# Usage: ./scripts/migrate_sqlite_to_postgres.sh
# - creates a JSON dump at backups/sqlite_data.json
# - prints the commands to provision Postgres / import data

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="$ROOT_DIR/backups"
mkdir -p "$BACKUP_DIR"

echo "1) Creating a JSON dump of the current Django DB (SQLite)"
echo "   This will be written to: $BACKUP_DIR/sqlite_data.json"

if [ ! -f "$ROOT_DIR/manage.py" ]; then
  echo "Error: manage.py not found in $ROOT_DIR" >&2
  exit 1
fi

# Use the project's venv python if present
PYTHON="${VENV_PY:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

echo "Running: $PYTHON manage.py dumpdata --natural-primary --natural-foreign --exclude auth.permission --exclude contenttypes --indent 2"
"$PYTHON" manage.py dumpdata --natural-primary --natural-foreign --exclude auth.permission --exclude contenttypes --indent 2 > "$BACKUP_DIR/sqlite_data.json"

echo
echo "Backup created: $BACKUP_DIR/sqlite_data.json"
echo
echo "NEXT STEPS (manual):"
echo "1. Provision a Postgres instance (managed DB, VM, or Docker). If using the included docker-compose.yml:"
echo "   - Install Docker Desktop / Docker Engine on your machine or the deployment host."
echo "   - Run: docker compose up -d db"
echo "   - The provided docker-compose uses: POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=hotel_project"
echo
echo "2. Set the DATABASE_URL environment variable for your shell or deployment environment (example for docker-compose above):"
echo "   export DATABASE_URL='postgres://postgres:postgres@127.0.0.1:5432/hotel_project'"
echo
echo "3. Run migrations against Postgres and create the schema:"
echo "   $PYTHON manage.py migrate --noinput"
echo
echo "4. Load the data dump into Postgres:"
echo "   $PYTHON manage.py loaddata backups/sqlite_data.json"
echo
echo "5. Copy media files (uploads) to your production storage (S3 or shared filesystem). Example (AWS CLI):"
echo "   aws s3 sync media/ s3://your-bucket/media/"
echo
echo "6. Verify data integrity and run tests. Once verified, update your deployment to use the new Postgres DATABASE_URL permanently."
echo
echo "Notes:"
echo "- If you have large BLOBs or complex data, consider using pgloader or a DB-level copy instead of dumpdata/loaddata."
echo "- For zero-downtime migrations between environments, schedule a maintenance window and repeat incremental syncs of media and changed data before cutover."

echo
echo "Script finished."
