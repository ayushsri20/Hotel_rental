#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # Exit on error

echo "=== Build Environment ==="
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la | head -20
echo

echo "Python version: $(python --version)"
echo "Python path: $(which python)"
echo "pip version: $(pip --version)"
echo

# Verify requirements.txt exists
if [ ! -f "requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in $(pwd)" >&2
  echo "Checking parent directories..."
  find . -name "requirements.txt" -type f 2>/dev/null || echo "requirements.txt not found anywhere"
  exit 1
fi

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
