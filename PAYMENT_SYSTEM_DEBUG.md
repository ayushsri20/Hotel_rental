# Payment System Debug Guide

## Overview
The payment system has two main operations:
1. **Create Monthly Payment** - Create a rent payment record for a room/month
2. **Record Payment** - Record an actual payment against a monthly payment record

## Database Models

### MonthlyPayment
- `room` - Foreign key to Room
- `guest` - Foreign key to Guest (optional)
- `month` - DateField (the month for which rent is due)
- `rent_amount` - Decimal (total rent amount due)
- `paid_amount` - Decimal (total amount paid so far)
- `payment_status` - CharField (pending/partial/paid/overdue)
- `paid_date` - DateField (when it was fully paid)
- `notes` - TextField

### PaymentRecord
- `monthly_payment` - Foreign key to MonthlyPayment
- `payment_date` - DateField (**Important: must be valid date**)
- `payment_amount` - Decimal (amount paid in this record)
- `payment_method` - CharField (cash/check/bank_transfer/upi/card)
- `reference_number` - CharField (optional)
- `notes` - TextField
- `created_by` - Foreign key to User
- `created_at` - DateTimeField (auto-set)

## Common Issues & Solutions

### Issue 1: Payment Date Not Being Stored
**Problem**: Payment records are created but with NULL or incorrect dates

**Solution**:
1. Ensure date is in ISO format `YYYY-MM-DD`
2. JavaScript converts date input to ISO string: `new Date().toISOString().split('T')[0]`
3. Django backend expects string in `%Y-%m-%d` format
4. Date is parsed before being saved to database

**Files to Check**:
- Template: `/rental/templates/manage_payments.html` (lines 520-521, 640-644)
- View: `/rental/views.py` (lines 413-490)

### Issue 2: Form Submission Returning 400 Error
**Problem**: Form submission fails with 400 Bad Request

**Debug Steps**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Submit the form
4. Look for log messages showing form data being sent
5. Check Network tab for the POST request to `/api/payment/create/`
6. Look at response to see error message

**Common Causes**:
- Missing CSRF token (should be auto-included in form)
- Invalid room ID
- Invalid month format (should be YYYY-MM-01)
- Rent amount ≤ 0

### Issue 3: Payment Amount Not Updating in UI
**Problem**: After recording payment, paid_amount doesn't update

**Solution**:
1. Page reload happens automatically (1.5s delay)
2. Check DevTools Network tab to confirm POST succeeded with 200 status
3. Check database directly:
   ```bash
   python3 manage.py shell
   from rental.models import MonthlyPayment
   p = MonthlyPayment.objects.first()
   print(f"Paid: {p.paid_amount}, Status: {p.payment_status}")
   ```

## Testing Procedures

### Test 1: Create a Monthly Payment via UI
1. Go to `/manage-payments/`
2. Select Room from dropdown
3. Select Month using month picker (should show as YYYY-MM)
4. Enter Rent Amount (e.g., 6000)
5. Click "Create Payment Record"
6. Check browser console for debug logs
7. Verify success message appears

### Test 2: Create a Monthly Payment via Shell
```bash
cd /Users/ayush/hotel_rental/hotel_project
python3 << 'EOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import MonthlyPayment, Room
from datetime import date

room = Room.objects.first()
payment, created = MonthlyPayment.objects.get_or_create(
    room=room,
    month=date(2025, 11, 1),
    defaults={'rent_amount': 6000}
)
print(f"Created: {created}, ID: {payment.id}")
EOF
```

### Test 3: Record a Payment via UI
1. After creating a monthly payment, click "Record Payment" button
2. Modal opens with default date set to today
3. Enter Amount (e.g., 3000 for partial payment)
4. Select Payment Method
5. Enter optional Reference Number
6. Click "Record Payment"
7. Check console for debug logs
8. Verify success message and page reloads

### Test 4: Record a Payment via Shell
```bash
cd /Users/ayush/hotel_rental/hotel_project
python3 << 'EOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import MonthlyPayment, PaymentRecord
from django.contrib.auth.models import User
from datetime import date

payment = MonthlyPayment.objects.first()
user = User.objects.filter(is_staff=True).first()

if payment and user:
    # Create payment record
    record = PaymentRecord.objects.create(
        monthly_payment=payment,
        payment_date=date(2025, 11, 14),  # Must be valid date
        payment_amount=3000,
        payment_method='cash',
        reference_number='REF001',
        created_by=user
    )
    
    # Update monthly payment
    payment.paid_amount += record.payment_amount
    if payment.paid_amount >= payment.rent_amount:
        payment.payment_status = 'paid'
        payment.paid_date = record.payment_date
    elif payment.paid_amount > 0:
        payment.payment_status = 'partial'
    payment.save()
    
    print(f"Record created: {record.id}")
    print(f"Payment updated: {payment.paid_amount} / {payment.rent_amount}")
EOF
```

### Test 5: Check Database Records
```bash
cd /Users/ayush/hotel_rental/hotel_project
python3 << 'EOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import MonthlyPayment, PaymentRecord

print("=== Monthly Payments ===")
for p in MonthlyPayment.objects.all()[:5]:
    print(f"Room {p.room.number} - {p.month}: ₹{p.paid_amount}/{p.rent_amount} ({p.payment_status})")

print("\n=== Payment Records ===")
for r in PaymentRecord.objects.all()[:5]:
    print(f"{r.payment_date} ({r.payment_method}): ₹{r.payment_amount} - {r.reference_number}")
EOF
```

## Date Format Reference

| Format | Example | Use Case |
|--------|---------|----------|
| `YYYY-MM-DD` | 2025-11-14 | Database storage, form submission |
| `YYYY-MM` | 2025-11 | HTML month input value |
| `%Y-%m-%d` | Python datetime.strptime format | Backend parsing |
| `%Y-%m` | Python datetime.strptime format | Backend parsing (month only) |

## Important Files

1. **Template**: `/rental/templates/manage_payments.html`
   - Form elements (lines 437-478 for create, 510-543 for record)
   - JavaScript handlers (lines 590-665)
   - Date handling (lines 640-644)

2. **Views**: `/rental/views.py`
   - `create_monthly_payment()` - lines 368-435
   - `record_payment()` - lines 410-490

3. **Models**: `/rental/models.py`
   - `MonthlyPayment` class
   - `PaymentRecord` class
   - `ElectricityBill` class

4. **URLs**: `/hotel_project/urls.py`
   - `/api/payment/create/` → `create_monthly_payment`
   - `/api/payment/record/` → `record_payment`

## Browser Console Testing

When testing via UI, open DevTools console to see:
```javascript
// Create form submission
Form Data being sent:
room_id: 49
month: 2025-11-01
rent_amount: 6000
csrfmiddlewaretoken: <token>

Response status: 200
Response data: {success: true, message: "...", payment: {...}}
```

```javascript
// Record payment submission
Payment Record Form Data being sent:
payment_id: 1
payment_amount: 3000
payment_date: 2025-11-14
payment_method: cash
reference_number: TEST001
notes: Test payment
csrfmiddlewaretoken: <token>

Response status: 200
Response data: {success: true, message: "...", payment: {...}}
```

## Troubleshooting Checklist

- [ ] Admin user logged in (check `/admin/` access)
- [ ] Rooms exist in database (should show in dropdown)
- [ ] No JavaScript errors in console
- [ ] CSRF token present in forms
- [ ] Date format is ISO (YYYY-MM-DD)
- [ ] Payment amount > 0
- [ ] Database has PaymentRecord table (check via `python3 manage.py migrate`)
- [ ] API endpoints return 200 (not 400, 403, 404)
