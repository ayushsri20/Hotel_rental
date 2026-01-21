#!/usr/bin/env bash
# Simple backup script for production DBs.
# - If DATABASE_URL points to Postgres, this uses pg_dump (requires pg_dump in PATH).
# - If using SQLite, it copies the sqlite file.

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
BACKUP_DIR=${BACKUP_DIR:-"$(pwd)/backups"}
mkdir -p "$BACKUP_DIR"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL not set. Exiting."
  exit 1
fi

echo "Backing up database at $TIMESTAMP to $BACKUP_DIR"

if [[ "$DATABASE_URL" =~ ^sqlite ]]; then
  # sqlite:///absolute/path or sqlite:///:memory:
  # Extract path
  SQLPATH=${DATABASE_URL#sqlite:///}
  if [ -z "$SQLPATH" ]; then
    echo "SQLite in-memory DB or invalid path; cannot back up" >&2
    exit 1
  fi
  cp "$SQLPATH" "$BACKUP_DIR/db.sqlite3.$TIMESTAMP" && echo "SQLite DB copied to $BACKUP_DIR/db.sqlite3.$TIMESTAMP"
  exit 0
fi

if [[ "$DATABASE_URL" =~ ^postgres ]]; then
  # Expect format: postgres://user:pass@host:port/dbname
  # Use pg_dump
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump not found in PATH. Please install postgresql client tools." >&2
    exit 2
  fi

  # Use environment for pg_dump if DATABASE_URL provided
  # The simplest is to pass the DATABASE_URL to pg_dump via PGPASSWORD and host/user flags — but pg_dump supports a connection string.
  OUTFILE="$BACKUP_DIR/pg_backup_$TIMESTAMP.sql"
  echo "Running pg_dump to $OUTFILE"
  pg_dump "$DATABASE_URL" -Fc -f "$OUTFILE"
  echo "Postgres backup complete: $OUTFILE"
  exit 0
fi

echo "Unsupported DATABASE_URL scheme. Please extend this script for your DB type." >&2
exit 3
