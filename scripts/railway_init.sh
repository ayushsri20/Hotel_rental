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
# Using a python one-liner for simplicity
echo "Checking superuser..."
python manage.py shell -c "
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
"

echo "=== Initialization Complete ==="
