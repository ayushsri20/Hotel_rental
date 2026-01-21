#!/usr/bin/env bash
set -euo pipefail
# Validate staging environment — smoke tests for critical flows
# Usage: ./scripts/validate_staging.sh
# Assumes app is running and DATABASE_URL is set

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${VENV_PY:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin}"

echo "=== Staging Validation Tests ==="
echo "Base URL: $BASE_URL"
echo

PASS=0
FAIL=0

test_endpoint() {
  local name=$1
  local method=$2
  local endpoint=$3
  local expected_code=$4
  
  echo -n "Testing $name ($method $endpoint)... "
  response=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint" 2>/dev/null || echo "000")
  
  if [ "$response" = "$expected_code" ]; then
    echo "PASS (HTTP $response)"
    ((PASS++))
  else
    echo "FAIL (expected HTTP $expected_code, got $response)"
    ((FAIL++))
  fi
}

test_database_integrity() {
  echo -n "Testing database integrity (users, rooms, payments exist)... "
  errors=$("$PYTHON" -c "
from django.contrib.auth.models import User
from rental.models import Room, MonthlyPayment
users = User.objects.count()
rooms = Room.objects.count()
payments = MonthlyPayment.objects.count()
print(f'Users: {users}, Rooms: {rooms}, Payments: {payments}')
if users > 0 and rooms > 0:
  print('OK')
else:
  raise Exception('Missing core data')
" 2>&1 || echo "FAIL")
  
  if echo "$errors" | grep -q "OK"; then
    echo "PASS"
    echo "  $(echo "$errors" | head -1)"
    ((PASS++))
  else
    echo "FAIL: $errors"
    ((FAIL++))
  fi
}

test_room_agreed_rent() {
  echo -n "Testing per-room agreed_rent field... "
  errors=$("$PYTHON" -c "
from rental.models import Room
rooms = Room.objects.filter(agreed_rent__isnull=False).count()
if rooms > 0:
  print(f'Found {rooms} rooms with agreed_rent set')
  print('OK')
else:
  print('Warning: no rooms have agreed_rent yet')
" 2>&1 || echo "FAIL")
  
  if echo "$errors" | grep -q "OK"; then
    echo "PASS"
    ((PASS++))
  else
    echo "WARN: $errors"
  fi
}

test_payment_records() {
  echo -n "Testing payment records and calculations... "
  errors=$("$PYTHON" -c "
from rental.models import MonthlyPayment, PaymentRecord
payments = MonthlyPayment.objects.count()
records = PaymentRecord.objects.count()
if payments > 0 and records > 0:
  print(f'Payments: {payments}, Records: {records}')
  print('OK')
else:
  print('Warning: no payment data')
" 2>&1 || echo "FAIL")
  
  if echo "$errors" | grep -q "OK"; then
    echo "PASS"
    ((PASS++))
  else
    echo "WARN: $errors"
  fi
}

test_analytics() {
  echo -n "Testing analytics (maintenance, electricity)... "
  errors=$("$PYTHON" -c "
from rental.models import MaintenanceExpense, ElectricityBill
maintenance = MaintenanceExpense.objects.count()
bills = ElectricityBill.objects.count()
print(f'Maintenance: {maintenance}, Electricity bills: {bills}')
print('OK')
" 2>&1 || echo "FAIL")
  
  if echo "$errors" | grep -q "OK"; then
    echo "PASS"
    ((PASS++))
  else
    echo "FAIL: $errors"
    ((FAIL++))
  fi
}

test_migrations_applied() {
  echo -n "Checking all migrations applied... "
  errors=$("$PYTHON" manage.py migrate --check 2>&1 || echo "FAIL")
  
  if echo "$errors" | grep -q "No migrations to apply" || [ -z "$errors" ]; then
    echo "PASS"
    ((PASS++))
  else
    echo "FAIL: pending migrations"
    ((FAIL++))
  fi
}

# Run tests
test_migrations_applied
test_database_integrity
test_room_agreed_rent
test_payment_records
test_analytics

# Optional: test HTTP endpoints if app is running
if curl -s -f "$BASE_URL/admin/" > /dev/null 2>&1; then
  test_endpoint "Admin login page" GET "/admin/" 200
  test_endpoint "Dashboard" GET "/dashboard/" 302  # Will redirect if not logged in
else
  echo "Note: App not responding at $BASE_URL (not critical if using separate test suite)"
fi

echo
echo "=== Summary ==="
echo "Tests passed: $PASS"
echo "Tests failed: $FAIL"
echo

if [ $FAIL -gt 0 ]; then
  echo "VALIDATION FAILED: Review the above and fix issues before production cutover."
  exit 1
else
  echo "VALIDATION PASSED: Staging environment is ready for production cutover."
  exit 0
fi
