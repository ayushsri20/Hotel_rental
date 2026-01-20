#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

echo "Python version: $(python --version)"
echo "Python path: $(which python)"
echo

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo
echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo
echo "=== Verifying WSGI module ==="
python -c "from hotel_project.wsgi import application; print('WSGI application loaded successfully')"

echo
echo "=== Build completed successfully ==="
