#!/usr/bin/env bash
set -euo pipefail
# Pre-migration safety check — ensures conditions are safe before pointing app to Postgres
# Usage: ./scripts/pre_migration_check.sh
# Exit 0 if safe; exit non-zero if risks detected

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${VENV_PY:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

echo "=== Pre-Migration Safety Check ==="
echo

PASS=0
FAIL=0

check_required_env() {
  local var_name=$1
  if [ -z "${!var_name-}" ]; then
    echo "FAIL: $var_name is not set. Set it before migration." >&2
    ((FAIL++))
    return 1
  fi
  echo "PASS: $var_name is set"
  return 0
}

check_env_value() {
  local var_name=$1
  local expected=$2
  local actual="${!var_name-}"
  if [ "$actual" != "$expected" ]; then
    echo "FAIL: $var_name should be '$expected', got '$actual'" >&2
    ((FAIL++))
    return 1
  fi
  echo "PASS: $var_name = $expected"
  return 0
}

# 1. Check SECRET_KEY
check_required_env SECRET_KEY && ((PASS++)) || true

# 2. Check DEBUG = false
check_env_value DEBUG false && ((PASS++)) || true

# 3. Check ALLOWED_HOSTS is set
check_required_env ALLOWED_HOSTS && ((PASS++)) || true

# 4. Check DATABASE_URL points to Postgres (not SQLite)
if [ -n "${DATABASE_URL-}" ]; then
  if [[ "$DATABASE_URL" == postgres* ]]; then
    echo "PASS: DATABASE_URL points to Postgres"
    ((PASS++))
  else
    echo "FAIL: DATABASE_URL does not point to Postgres (must be postgres://...)" >&2
    ((FAIL++))
  fi
else
  echo "FAIL: DATABASE_URL is not set" >&2
  ((FAIL++))
fi

# 5. Check SQLite backup exists
if [ -f "$ROOT_DIR/backups/sqlite_data.json" ]; then
  size=$(stat -f%z "$ROOT_DIR/backups/sqlite_data.json" 2>/dev/null || stat -c%s "$ROOT_DIR/backups/sqlite_data.json" 2>/dev/null || echo 0)
  if [ "$size" -gt 100 ]; then
    echo "PASS: SQLite backup exists ($(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo $size bytes))"
    ((PASS++))
  else
    echo "FAIL: SQLite backup too small or empty" >&2
    ((FAIL++))
  fi
else
  echo "FAIL: backups/sqlite_data.json does not exist. Create backup first (env -u DATABASE_URL python manage.py dumpdata...)" >&2
  ((FAIL++))
fi

# 6. Try to connect to Postgres (will fail if credentials wrong)
echo -n "Checking Postgres connectivity... "
if "$PYTHON" -c "import psycopg; psycopg.connect('$DATABASE_URL', autocommit=True)" 2>/dev/null; then
  echo "PASS"
  ((PASS++))
else
  echo "FAIL: Could not connect to Postgres. Check DATABASE_URL and credentials." >&2
  ((FAIL++))
fi

# 7. Check that media backup exists (warn if not)
if [ -d "$ROOT_DIR/media" ] && [ -n "$(find $ROOT_DIR/media -type f 2>/dev/null | head -1)" ]; then
  if [ -f "$ROOT_DIR/backups/media_backup.tar.gz" ] 2>/dev/null || [ -d "$ROOT_DIR/backups/media_backup" ] 2>/dev/null; then
    echo "PASS: Media backup exists"
    ((PASS++))
  else
    echo "WARN: Media files exist but no backup found. Create one: tar -czf backups/media_backup.tar.gz media/" >&2
  fi
fi

echo
echo "=== Summary ==="
echo "Checks passed: $PASS"
echo "Checks failed: $FAIL"
echo

if [ $FAIL -gt 0 ]; then
  echo "MIGRATION BLOCKED: Fix the above issues before proceeding." >&2
  exit 1
else
  echo "SAFE TO PROCEED: All pre-migration checks passed."
  echo "Next: run ./scripts/deploy_production.sh"
  exit 0
fi
