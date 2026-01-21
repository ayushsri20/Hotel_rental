#!/usr/bin/env bash
set -euo pipefail
# Backup retention policy — archive old backups with metadata for safe recovery
# Usage: ./scripts/manage_backups.sh [RETENTION_DAYS]
# Default: keep backups for 90 days; archive older ones

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="$ROOT_DIR/backups"
ARCHIVE_DIR="$BACKUP_DIR/archived"
RETENTION_DAYS="${1:-90}"

echo "=== Backup Retention & Archive Management ==="
echo "Backup directory: $BACKUP_DIR"
echo "Retention period: $RETENTION_DAYS days"
echo "Archiving older backups to: $ARCHIVE_DIR"
echo

mkdir -p "$BACKUP_DIR" "$ARCHIVE_DIR"

# Create archive metadata log
METADATA="$ARCHIVE_DIR/metadata.log"
if [ ! -f "$METADATA" ]; then
  echo "# Backup Archive Metadata (created $(date))" > "$METADATA"
  echo "# Format: backup_file | archive_date | retention_end_date | notes" >> "$METADATA"
fi

# Find backups older than RETENTION_DAYS
echo "Scanning for backups older than $RETENTION_DAYS days..."
count=0

while IFS= read -r backup_file; do
  backup_name=$(basename "$backup_file")
  archive_date=$(date +%Y-%m-%d)
  archive_target="$ARCHIVE_DIR/${archive_date}_${backup_name}.gz"
  retention_end=$(date -d "+${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v+${RETENTION_DAYS}d +%Y-%m-%d)
  
  if [ -f "$archive_target" ]; then
    echo "  Already archived: $backup_name"
    ((count++))
  else
    echo "  Archiving: $backup_name"
    gzip -c "$backup_file" > "$archive_target"
    echo "$backup_name | $archive_date | $retention_end | auto-archived" >> "$METADATA"
    ((count++))
  fi
done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name "*.json" -o -name "*.dump" -mtime +$RETENTION_DAYS 2>/dev/null || true)

echo "Archived $count old backups."
echo

# Show active backups
echo "Active backups (retained for $RETENTION_DAYS days):"
while IFS= read -r backup_file; do
  size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo 0)
  mtime=$(stat -f%Sm -t "%Y-%m-%d %H:%M" "$backup_file" 2>/dev/null || stat -c%y "$backup_file" 2>/dev/null | cut -d' ' -f1-2 || echo "unknown")
  printf "  %-40s %12s %s\n" "$(basename "$backup_file")" "$size bytes" "$mtime"
done < <(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name "*.json" -o -name "*.dump" \) -mtime -$RETENTION_DAYS 2>/dev/null | sort)

echo
echo "Archive metadata:"
tail -n 5 "$METADATA" | sed 's/^/  /'

echo
echo "=== Backup Policy ==="
echo "- Backups older than $RETENTION_DAYS days are gzipped and archived to $ARCHIVE_DIR"
echo "- Archive metadata is logged in $METADATA"
echo "- SQLite dumps and pg_dumps should be created regularly (cron job recommended)"
echo "- Test restore from archives periodically"
echo
echo "To restore from an archived backup:"
echo "  gunzip $ARCHIVE_DIR/YYYY-MM-DD_backup.json.gz > /tmp/backup.json"
echo "  python manage.py loaddata /tmp/backup.json"
echo
