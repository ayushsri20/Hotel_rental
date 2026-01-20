#!/usr/bin/env bash
set -euo pipefail
# Render deployment diagnostic — validate all requirements before deploy
# Run this locally to catch issues early

echo "=== Render Deployment Diagnostic ==="
echo

# Check 1: build.sh exists and is executable
echo -n "Checking build.sh... "
if [ -f "./build.sh" ] && [ -x "./build.sh" ]; then
  echo "PASS"
else
  echo "FAIL"
  echo "ERROR: build.sh missing or not executable. Run: chmod +x build.sh" >&2
  exit 1
fi

# Check 2: render.yaml exists and is valid
echo -n "Checking render.yaml syntax... "
if command -v yq >/dev/null 2>&1; then
  if yq eval '.services[0].startCommand' render.yaml >/dev/null 2>&1; then
    echo "PASS"
  else
    echo "FAIL"
    echo "ERROR: render.yaml is invalid YAML" >&2
    exit 1
  fi
else
  if grep -q "startCommand" render.yaml; then
    echo "PASS (basic check)"
  else
    echo "FAIL"
    exit 1
  fi
fi

# Check 3: hotel_project/wsgi.py exists
echo -n "Checking hotel_project/wsgi.py... "
if [ -f "hotel_project/wsgi.py" ]; then
  echo "PASS"
else
  echo "FAIL"
  echo "ERROR: hotel_project/wsgi.py not found" >&2
  exit 1
fi

# Check 4: hotel_project/settings.py exists
echo -n "Checking hotel_project/settings.py... "
if [ -f "hotel_project/settings.py" ]; then
  echo "PASS"
else
  echo "FAIL"
  echo "ERROR: hotel_project/settings.py not found" >&2
  exit 1
fi

# Check 5: requirements.txt exists
echo -n "Checking requirements.txt... "
if [ -f "requirements.txt" ]; then
  echo "PASS"
  # Show key packages
  echo "  Key packages: $(grep -E 'Django|gunicorn|psycopg|whitenoise' requirements.txt | tr '\n' ' ')"
else
  echo "FAIL"
  echo "ERROR: requirements.txt not found" >&2
  exit 1
fi

# Check 6: Procfile exists (for reference)
echo -n "Checking Procfile... "
if [ -f "Procfile" ]; then
  echo "PASS"
  cat Procfile | sed 's/^/  /'
else
  echo "WARN: Procfile not found (optional for Render)"
fi

# Check 7: Verify settings reads DATABASE_URL
echo -n "Checking DATABASE_URL parsing in settings.py... "
if grep -q "DATABASE_URL\|dj_database_url" hotel_project/settings.py; then
  echo "PASS"
else
  echo "WARN: DATABASE_URL not parsed. Ensure settings.py handles Postgres connection."
fi

# Check 8: Verify SECRET_KEY fallback
echo -n "Checking SECRET_KEY handling... "
if grep -q "os.environ.get.*SECRET_KEY" hotel_project/settings.py; then
  echo "PASS"
else
  echo "WARN: SECRET_KEY should be read from environment for production"
fi

# Check 9: Verify DEBUG is false
echo -n "Checking DEBUG setting... "
if grep -q "DEBUG.*=.*os.environ.get\|DEBUG.*=.*False" hotel_project/settings.py; then
  echo "PASS"
else
  echo "WARN: DEBUG should be false in production settings"
fi

# Check 10: Verify gunicorn in requirements
echo -n "Checking gunicorn in requirements... "
if grep -q "gunicorn" requirements.txt; then
  echo "PASS"
else
  echo "FAIL"
  echo "ERROR: gunicorn not in requirements.txt. Add it: echo 'gunicorn>=21.0' >> requirements.txt" >&2
  exit 1
fi

# Check 11: Verify psycopg in requirements
echo -n "Checking psycopg in requirements... "
if grep -q "psycopg" requirements.txt; then
  echo "PASS"
else
  echo "FAIL"
  echo "ERROR: psycopg (postgres driver) not in requirements.txt. Add it: echo 'psycopg[binary]>=3.1' >> requirements.txt" >&2
  exit 1
fi

# Check 12: Verify staticfiles directory exists (or will be created)
echo -n "Checking staticfiles setup... "
if grep -q "STATIC_ROOT" hotel_project/settings.py; then
  echo "PASS"
else
  echo "WARN: STATIC_ROOT not configured. collectstatic may fail."
fi

echo
echo "=== Diagnostic Summary ==="
echo "All critical checks passed. Ready for Render deployment."
echo
echo "Next steps:"
echo "1. Commit and push to GitHub:"
echo "   git add render.yaml build.sh"
echo "   git commit -m 'Fix Render deployment config'"
echo "   git push origin main"
echo
echo "2. In Render dashboard:"
echo "   - Create a new Web Service"
echo "   - Connect your GitHub repo"
echo "   - Render will auto-detect render.yaml"
echo "   - Environment vars will be auto-populated from render.yaml"
echo
echo "3. Monitor deployment:"
echo "   - Dashboard → Service → Logs"
echo "   - Look for: 'Build completed', 'Starting gunicorn', 'listening on 0.0.0.0:10000'"
echo
echo "4. If deployment fails:"
echo "   - Check logs for specific error"
echo "   - Run ./scripts/pre_migration_check.sh locally"
echo "   - Ensure DATABASE_URL is correctly formatted"
echo
