#!/bin/bash
# Railway Initialization Script
# This script ensures the database is migrated and a superuser exists.

echo "=== Railway Initialization ==="

# 1. Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# 2. Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 3. Create superuser if it doesn't exist
echo "Checking superuser..."
PYTHON_CMD="python"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python3"
fi

$PYTHON_CMD manage.py shell -c "
try:
    from django.contrib.auth.models import User
    import os
    username = os.environ.get('SUPERUSER_USERNAME', 'ayush')
    email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f'Superuser {username} created.')
    else:
        print(f'Superuser {username} already exists.')
except Exception as e:
    print(f'Error checking superuser: {e}')
"

echo "=== Initialization Complete ==="
