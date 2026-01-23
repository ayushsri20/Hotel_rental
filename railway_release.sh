#!/bin/bash
set -e

echo "=== Railway Release Phase Starting ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo "DATABASE_URL present: ${DATABASE_URL:0:30}..."

echo "=== Running migrations ==="
python3 manage.py migrate --noinput --verbosity 2

echo "=== Collecting static files ==="
python3 manage.py collectstatic --noinput --verbosity 2

echo "=== Creating superuser ==="
python3 manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='ayush').exists():
    User.objects.create_superuser('ayush', 'admin@example.com', 'admin123')
    print('✓ Superuser created')
else:
    print('✓ Superuser already exists')
"

echo "=== Release phase complete ==="
