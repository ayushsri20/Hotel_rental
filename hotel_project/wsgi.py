"""
WSGI config for hotel_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path
import django

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')

# Ensure staticfiles directory exists before starting the application
# This is important for ephemeral filesystems like Railway
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'
if not STATIC_ROOT.exists():
    try:
        STATIC_ROOT.mkdir(parents=True, exist_ok=True)
        print(f"Created staticfiles directory: {STATIC_ROOT}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not create staticfiles directory: {e}", file=sys.stderr)

# Setup Django
django.setup()

# Test database connection
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✓ Database connection successful", file=sys.stderr)
except Exception as e:
    print(f"✗ Database connection failed: {e}", file=sys.stderr)
    raise

# Verify auth_user table exists - if not, try to run migrations
try:
    from django.db import connection
    from django.db.utils import ProgrammingError
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM auth_user LIMIT 1")
    print("✓ auth_user table exists", file=sys.stderr)
except (ProgrammingError, Exception) as e:
    print(f"⚠ auth_user table missing, attempting migrations...", file=sys.stderr)
    try:
        from django.core.management import call_command
        call_command('migrate', verbosity=2, interactive=False)
        print("✓ Migrations completed successfully", file=sys.stderr)
    except Exception as migrate_err:
        print(f"✗ Migration failed: {migrate_err}", file=sys.stderr)
        raise

application = get_wsgi_application()
