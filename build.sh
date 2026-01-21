#!/usr/bin/env bash
# Build script for Railway/Render deployment

set -o errexit  # Exit on error

echo "=== Build Environment ==="
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la | head -20
echo

# Change to hotel_project directory if we're in the root
if [ -d "hotel_project" ] && [ ! -f "requirements.txt" ]; then
  echo "Changing to hotel_project directory..."
  cd hotel_project
fi

echo "Python version: $(python --version)"
echo "Python path: $(which python)"
echo "pip version: $(pip --version)"
echo "Current directory: $(pwd)"
echo

# Verify requirements.txt exists
if [ ! -f "requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in $(pwd)" >&2
  echo "Contents of current directory:"
  ls -la
  exit 1
fi

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --clear --verbosity 2

echo
echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo
echo "=== Verifying WSGI module ==="
python -c "from hotel_project.wsgi import application; print('WSGI application loaded successfully')"

echo
echo "=== Build completed successfully ==="
