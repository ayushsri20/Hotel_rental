# Production Deployment Runbook (Safety-First)

Complete your migration from SQLite → Postgres without data loss. Follow all steps in order.

## Prerequisites (do NOW on your local machine)

1. **Backup SQLite data** (you already did this):
```bash
env -u DATABASE_URL python3 manage.py dumpdata --natural-foreign --natural-primary --exclude auth.permission --exclude contenttypes > backups/sqlite_data.json
```

2. **Backup media files** (do now):
```bash
tar -czf backups/media_backup.tar.gz media/
```

3. **Provision Postgres instance** (managed DB or your own):
   - Note the connection URL: `postgres://user:pass@host:5432/dbname`

## Deployment Sequence (on production host)

### Phase 1: Preparation (safe, can be run multiple times)

```bash
cd /path/to/project

# Export required environment variables
export SECRET_KEY='<very-secret-value>'
export DEBUG='false'
export ALLOWED_HOSTS='your.domain.com'
export DATABASE_URL='postgres://<user>:<pass>@<host>:5432/<dbname>'
# If using S3:
export AWS_S3_BUCKET_NAME='your-bucket'
export AWS_ACCESS_KEY_ID='AKIA...'
export AWS_SECRET_ACCESS_KEY='...'
export AWS_REGION='us-east-1'

# Activate virtualenv
source .venv/bin/activate
```

### Phase 2: Run Safety Checks (mandatory)

```bash
# This will block if any critical issues exist
./scripts/pre_migration_check.sh
```

**Expected output**: All checks pass, "SAFE TO PROCEED" message.

If any check fails, fix the issue and retry. Do not proceed without all checks passing.

### Phase 3: Deploy to Postgres (migrate + backup + static)

```bash
# This runs:
# - Pre-migration checks
# - Create logical backup (backups/production_data.json)
# - Run database migrations on Postgres
# - Collect static files
# - Sync media to S3 (if configured)
./scripts/deploy_production.sh
```

**Expected output**: Step 1-5 completed, clear next-steps printed.

### Phase 4: Validate Staging Environment (before cutover)

```bash
# Run smoke tests against the new Postgres DB
./scripts/validate_staging.sh
```

**Expected output**: All tests pass (database integrity, room fields, payment records, migrations applied).

If any test fails, review the error, fix the data or schema, and re-run.

### Phase 5: Test Restore / Rollback Plan

```bash
# Validate that backups can be restored (critical for safety)
./scripts/test_restore.sh backups/production_data.json
```

**Expected output**: "Restore rollback procedure documented and ready".

Keep this backup for at least 90 days. Archive older backups:
```bash
./scripts/manage_backups.sh 90
```

### Phase 6: Cutover (flip traffic to Postgres)

Once all validations pass:

1. **Stop the old app** (if still running on SQLite):
```bash
systemctl stop hotel_project
```

2. **Ensure DATABASE_URL points to Postgres** (should already be set in env or systemd unit).

3. **Restart the app with Postgres**:
```bash
systemctl start hotel_project
```

4. **Verify app is running**:
```bash
curl http://localhost:8000/admin/ | head -20
```

5. **Perform final smoke tests**:
   - Log into admin panel
   - Edit a room (change agreed_rent)
   - Create a payment
   - Check analytics dashboard
   - Monitor logs for errors

## Rollback Plan (if something goes wrong)

1. **Stop the app**:
```bash
systemctl stop hotel_project
```

2. **Revert DATABASE_URL to old connection** (SQLite or backup Postgres):
```bash
# Point back to SQLite or previous Postgres
unset DATABASE_URL
# or
export DATABASE_URL='<old_db_url>'
```

3. **Restart the app**:
```bash
systemctl start hotel_project
```

4. **If you need a full DB restore** (something corrupted in Postgres):
```bash
# Create fresh Postgres database
# Run migrations on fresh DB
export DATABASE_URL='postgres://user:pass@newhost:5432/newdb'
python manage.py migrate --noinput

# Load backup data
python manage.py loaddata backups/production_data.json
```

5. **Restore media from backup** (if used S3):
```bash
tar -xzf backups/media_backup.tar.gz -C .
aws s3 sync media/ s3://your-bucket/media/ --acl private
```

## Backup & Maintenance (ongoing)

### Daily DB Backups (Postgres)

Create `/etc/cron.daily/hotel_project_backup`:
```bash
#!/bin/sh
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PGHOST='<db_host>'
export PGPORT=5432
export PGUSER='<db_user>'
export PGPASSWORD='<db_pass>'
export PGDATABASE='hotel_project'

BACKUP_DIR="/var/backups/hotel_project"
mkdir -p "$BACKUP_DIR"

pg_dump -Fc -f "$BACKUP_DIR/$(date +\%F)-hotel_project.dump"
find "$BACKUP_DIR" -mtime +90 -delete
```

Make it executable:
```bash
chmod +x /etc/cron.daily/hotel_project_backup
```

### Media Backups (S3)

```bash
# Sync media to S3 daily
aws s3 sync media/ s3://your-bucket/media/ --acl private
```

Or set up an AWS Backup policy for automated snapshots.

### Periodic Restore Tests

Monthly, test restore from backup:
```bash
pg_restore --version  # Verify pg_restore is installed
# Create a test database and restore to validate backups work
pg_restore -d hotel_project_test /var/backups/hotel_project/2026-01-20-hotel_project.dump
```

## Safety Checklist

- [ ] Pre-migration checks pass
- [ ] Staging validation tests pass
- [ ] Restore test validates backup integrity
- [ ] Media backup created and stored safely
- [ ] Smoke tests on production verified
- [ ] Rollback plan tested
- [ ] Daily backups configured
- [ ] Monitoring/alerts configured
- [ ] Data validated for 24 hours (no emergency restore needed) — then delete SQLite backup

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| `CONNECTION REFUSED` | Check DATABASE_URL, verify Postgres host is reachable, test with `psql` |
| `PERMISSION DENIED` | Verify db user credentials, check Postgres user permissions |
| `MIGRATIONS NOT APPLIED` | Run `python manage.py migrate --noinput` explicitly |
| `LOADDATA FAILS` | Check fixture format, review error, try smaller fixtures, check FK constraints |
| `MEDIA NOT SYNCING` | Verify AWS credentials, check `aws s3 ls s3://bucket/`, ensure IAM permissions |

## Support & Monitoring

After cutover:
- Monitor Django logs for errors
- Monitor Postgres slow queries
- Set up Sentry for error tracking (optional but recommended)
- Alert on backup failures
- Test restores monthly
