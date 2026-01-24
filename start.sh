#!/bin/bash
set -e  # Exit immediately if any command fails

echo "========================================="
echo "Starting Railway Deployment"
echo "========================================="
echo "Working Directory: $(pwd)"
echo "Python: $(python3 --version)"
echo "Django: $(python3 -c 'import django; print(django.get_version())')"

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    exit 1
else
    echo "✓ DATABASE_URL is set (first 40 chars): ${DATABASE_URL:0:40}..."
fi

echo ""
echo "========================================="
echo "Running Database Migrations"
echo "========================================="
python3 manage.py migrate --noinput --verbosity 2
if [ $? -ne 0 ]; then
    echo "ERROR: Migrations failed!"
    exit 1
fi
echo "✓ Migrations completed successfully"

echo ""
echo "========================================="
echo "Collecting Static Files"
echo "========================================="
python3 manage.py collectstatic --noinput --clear
echo "✓ Static files collected"

echo ""
echo "========================================="
echo "Creating Superuser"
echo "========================================="
python3 manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='ayush').exists():
    User.objects.create_superuser('ayush', 'admin@example.com', 'admin123')
    print('✓ Superuser created: ayush')
else:
    print('✓ Superuser already exists: ayush')
EOF

echo ""
echo "========================================="
echo "Starting Gunicorn Web Server"
echo "========================================="
exec gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} hotel_project.wsgi:application

echo ""
echo "========================================="
echo "Loading Sample Room Data"
echo "========================================="
python3 load_sample_data.py || echo "Sample data already loaded or error occurred"
