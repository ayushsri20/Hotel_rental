#!/usr/bin/env bash
set -euo pipefail
# Safe production deploy helper (idempotent, creates backups and runs migrations)
# SAFETY ENFORCEMENT: Calls pre-migration checks and prevents cutover until validated
# Usage: sudo ./scripts/deploy_production.sh  (or run as the deploy user)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${VENV_PY:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

echo "=== Production Deploy Helper (Safety-First) ==="
echo
echo "WARNING: This script will migrate data from SQLite to Postgres."
echo "         Ensure you have read backups and validated staging environment first."
echo

# Step 0: Run pre-migration safety checks (mandatory)
echo "Step 1/5: Running pre-migration safety checks..."
if ! "$ROOT_DIR/scripts/pre_migration_check.sh"; then
  echo
  echo "DEPLOYMENT BLOCKED: Pre-migration checks failed." >&2
  echo "Fix the issues above and try again." >&2
  exit 1
fi

echo
echo "Step 2/5: Creating application data backup..."

check_env_var() {
  local name=$1
  if [ -z "${!name-}" ]; then
    echo "ERROR: $name is not set" >&2
    return 1
  fi
}

if ! check_env_var SECRET_KEY; then
  echo "Set SECRET_KEY before running this script." >&2
  exit 1
fi

# DEBUG must be false in production
if [ "${DEBUG-}" ]; then
  lower=$(echo "$DEBUG" | tr '[:upper:]' '[:lower:]')
  if [ "$lower" = "1" ] || [ "$lower" = "true" ] || [ "$lower" = "yes" ]; then
    echo "ERROR: DEBUG is true. Set DEBUG=false in production." >&2
    exit 1
  fi
fi

echo "Creating application data backup (logical) to backups/production_data.json"
mkdir -p backups
"$PYTHON" manage.py dumpdata --natural-primary --natural-foreign --exclude auth.permission --exclude contenttypes --indent 2 > backups/production_data.json
echo "Backup saved: backups/production_data.json"

echo
echo "Step 3/5: Running database migrations..."
"$PYTHON" manage.py migrate --noinput

echo
echo "Step 4/5: Collecting static files..."
"$PYTHON" manage.py collectstatic --noinput

echo
echo "Step 5/5: Syncing media to durable storage..."
if [ -n "${AWS_S3_BUCKET_NAME-}" ] && command -v aws >/dev/null 2>&1; then
  echo "Syncing media/ to S3 bucket $AWS_S3_BUCKET_NAME"
  aws s3 sync media/ s3://$AWS_S3_BUCKET_NAME/media/ --acl private
  echo "Media synced to S3://$AWS_S3_BUCKET_NAME/media/"
else
  echo "AWS S3 not configured or awscli missing; skipping media sync."
  echo "Remember to sync media manually or configure AWS_S3_BUCKET_NAME."
fi

echo
echo "=========================================="
echo "Deploy preparation completed successfully!"
echo "=========================================="
echo
echo "NEXT STEPS BEFORE PRODUCTION CUTOVER:"
echo
echo "1. Validate staging environment with:"
echo "     ./scripts/validate_staging.sh"
echo
echo "2. Test database restore/rollback with:"
echo "     ./scripts/test_restore.sh backups/production_data.json"
echo
echo "3. Archive old backups with:"
echo "     ./scripts/manage_backups.sh"
echo
echo "4. Perform smoke tests on all key flows:"
echo "     - Edit room number and agreed_rent"
echo "     - Create a payment and verify calculations"
echo "     - Record maintenance expense"
echo "     - Verify analytics dashboard"
echo
echo "5. Once validated, point the live app to DATABASE_URL (switch DNS/load balancer)"
echo
echo "ROLLBACK PLAN (if something goes wrong):"
echo "     1. Revert DATABASE_URL to old SQLite or a backup Postgres"
echo "     2. Restore media from backup"
echo "     3. Keep backups/production_data.json for 90 days minimum"
echo
echo "Backup file: backups/production_data.json"
echo "Keep this file for 90+ days in case of emergency restore."
echo
