"""
Performance Dashboard Views
Handles all room collection, payment, and expense analytics
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Sum, F, Case, When, DecimalField, Count
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import Room, Guest, MonthlyPayment, PaymentRecord, ElectricityBill, MaintenanceExpense

def is_admin(user):
    """Check if user is admin"""
    return user.is_staff or user.is_superuser

@login_required(login_url='login')
@user_passes_test(is_admin)
def performance_dashboard(request):
    """
    Performance dashboard showing:
    - Total collection and expenses
    - Room-wise collection analysis
    - Payment status by room
    - Electricity bill tracking
    - Building complex summary
    """
    
    try:
        # Get all rooms
        all_rooms = Room.objects.all().order_by('number')
        total_rooms = all_rooms.count()
        occupied_rooms = Guest.objects.filter(room__isnull=False, is_active=True).count()
        
        # Calculate total collections
        total_collected = PaymentRecord.objects.aggregate(
            total=Sum('payment_amount', output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        # Get current month data
        today = date.today()
        current_month = date(today.year, today.month, 1)
        
        # Collection analysis by room
        room_collections = []
        # Use Decimal accumulators to avoid float rounding errors
        acc_expected_monthly = Decimal('0.00')
        acc_collected_this_month = Decimal('0.00')
        acc_pending_amount = Decimal('0.00')
        for room in all_rooms:
            guest = Guest.objects.filter(room=room, is_active=True).first()
            
            # Get monthly payment for current month
            monthly_payment = MonthlyPayment.objects.filter(
                room=room,
                month=current_month
            ).first()
            
            if monthly_payment:
                monthly_rent = monthly_payment.rent_amount
                collected = monthly_payment.paid_amount
                pending = monthly_payment.remaining_amount()
                payment_status = monthly_payment.payment_status
                monthly_payment_id = monthly_payment.id
            else:
                # No payment record, prefer room's agreed_rent if set, otherwise use room.price
                monthly_rent = room.agreed_rent if getattr(room, 'agreed_rent', None) is not None else room.price
                collected = Decimal('0.00')
                pending = monthly_rent
                payment_status = 'pending'
                monthly_payment_id = None
            
            # Calculate collection percentage
            if monthly_rent > 0:
                collection_percentage = int((collected / monthly_rent) * 100)
            else:
                collection_percentage = 0
            
            # Ensure percentage doesn't exceed 100
            collection_percentage = min(collection_percentage, 100)
            
            # update Decimal accumulators before converting to floats for the template
            acc_expected_monthly += Decimal(monthly_rent)
            acc_collected_this_month += Decimal(collected)
            acc_pending_amount += Decimal(pending)

            room_data = {
                'room_number': room.number,
                'guest_name': f"{guest.first_name} {guest.last_name}" if guest else "Vacant",
                'monthly_rent': float(monthly_rent),
                'collected': float(collected),
                'pending': float(pending),
                'collection_percentage': collection_percentage,
                'payment_status': payment_status,
                'monthly_payment_id': monthly_payment_id,
            }
            room_collections.append(room_data)
        
        # Calculate summary statistics using Decimal accumulators
        total_collection = acc_collected_this_month
        pending_amount = acc_pending_amount
        
        expected_monthly_collection = acc_expected_monthly
        collected_this_month = acc_collected_this_month
        
        # Calculate collection efficiency
        if expected_monthly_collection > 0:
            collection_efficiency = int((collected_this_month / expected_monthly_collection) * 100)
        else:
            collection_efficiency = 0
        
        # Get overdue payments (past due date)
        overdue_payments = MonthlyPayment.objects.filter(
            payment_status__in=['pending', 'partial'],
            paid_date__isnull=True
        ).filter(month__lt=current_month)
        
        overdue_amount = Decimal('0.00')
        for p in overdue_payments:
            overdue_amount += p.remaining_amount()
        
        # Get electricity bills data
        electricity_bills = []
        bills = ElectricityBill.objects.select_related('room', 'guest').order_by('-month')[:20]
        
        total_bills_pending = Decimal('0.00')
        
        for bill in bills:
            bill_data = {
                'bill_id': bill.id,
                'room_number': bill.room.number,
                'month': bill.month,
                'units_consumed': float(bill.units_consumed),
                'bill_amount': float(bill.bill_amount),
                'paid_amount': float(bill.paid_amount),
                'remaining': float(bill.remaining_amount()),
                'bill_status': bill.bill_status,
            }
            electricity_bills.append(bill_data)
            
            if bill.bill_status in ['pending', 'partial']:
                total_bills_pending += bill.remaining_amount()
        
        # Structured context for easier template consumption
        context = {
            'kpis': {
                'total_collection': float(total_collection),
                'all_time_collection': float(total_collected),
                'total_rooms': total_rooms,
                'occupied_rooms': occupied_rooms,
                'pending_amount': float(pending_amount),
                'overdue_amount': float(overdue_amount),
                'total_bills': float(total_bills_pending),
                'collection_efficiency': collection_efficiency,
            },
            'summary': {
                'expected_monthly_collection': float(expected_monthly_collection),
                'collected_this_month': float(collected_this_month),
            },
            'rooms': room_collections,
            'bills': electricity_bills,
            'meta': {
                'generated_at': datetime.now().isoformat(),
            },

            # Backwards compatibility: keep previous flat keys
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'total_collection': float(total_collection),
            'pending_amount': float(pending_amount),
            'overdue_amount': float(overdue_amount),
            'total_bills': float(total_bills_pending),
            'room_collections': room_collections,
            'expected_monthly_collection': float(expected_monthly_collection),
            'collected_this_month': float(collected_this_month),
            'collection_efficiency': collection_efficiency,
            'electricity_bills': electricity_bills,
        }
        
        return render(request, 'performance_dashboard.html', context)
    
    except Exception as e:
        print(f"Error in performance_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return with empty context on error
        context = {
            'kpis': {
                'total_collection': 0,
                'total_rooms': 0,
                'occupied_rooms': 0,
                'pending_amount': 0,
                'overdue_amount': 0,
                'total_bills': 0,
                'collection_efficiency': 0,
            },
            'summary': {
                'expected_monthly_collection': 0,
                'collected_this_month': 0,
            },
            'rooms': [],
            'bills': [],
            'meta': {
                'generated_at': datetime.now().isoformat(),
            },
            # Backwards compatibility
            'total_rooms': 0,
            'occupied_rooms': 0,
            'total_collection': 0,
            'pending_amount': 0,
            'overdue_amount': 0,
            'total_bills': 0,
            'room_collections': [],
            'expected_monthly_collection': 0,
            'collected_this_month': 0,
            'collection_efficiency': 0,
            'electricity_bills': [],
            'error': str(e),
        }
        return render(request, 'performance_dashboard.html', context)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def record_payment_from_dashboard(request):
    """Record payment from performance dashboard"""
    try:
        monthly_payment_id = request.POST.get('monthly_payment_id')
        payment_amount = request.POST.get('payment_amount')
        payment_method = request.POST.get('payment_method', 'cash')
        reference_number = request.POST.get('reference_number', '').strip()
        payment_date_str = request.POST.get('payment_date')
        notes = request.POST.get('notes', '').strip()
        
        # Validate inputs
        if not monthly_payment_id or not payment_amount:
            return JsonResponse({
                'success': False,
                'message': 'Monthly payment ID and amount are required'
            }, status=400)
        
        try:
            payment_amount = Decimal(payment_amount)
            if payment_amount <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Payment amount must be greater than 0'
                }, status=400)
        except:
            return JsonResponse({
                'success': False,
                'message': 'Invalid payment amount'
            }, status=400)
        
        # Parse payment date
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except:
            return JsonResponse({
                'success': False,
                'message': 'Invalid payment date format'
            }, status=400)
        
        # Get monthly payment
        monthly_payment = get_object_or_404(MonthlyPayment, id=monthly_payment_id)
        
        # Check if payment amount doesn't exceed remaining
        if payment_amount > monthly_payment.remaining_amount():
            return JsonResponse({
                'success': False,
                'message': f'Payment amount exceeds remaining balance of ₹{monthly_payment.remaining_amount()}'
            }, status=400)
        
        # Create payment record
        payment_record = PaymentRecord.objects.create(
            monthly_payment=monthly_payment,
            payment_date=payment_date,
            payment_amount=payment_amount,
            payment_method=payment_method,
            reference_number=reference_number,
            notes=notes,
            created_by=request.user
        )
        
        # Update monthly payment
        monthly_payment.paid_amount += payment_amount
        
        # Update payment status
        if monthly_payment.paid_amount >= monthly_payment.rent_amount:
            monthly_payment.payment_status = 'paid'
            monthly_payment.paid_date = payment_date
        elif monthly_payment.paid_amount > 0:
            monthly_payment.payment_status = 'partial'
        
        monthly_payment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Payment of ₹{payment_amount} recorded successfully',
            'payment_record_id': payment_record.id
        })
    
    except Exception as e:
        print(f"Error recording payment: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error recording payment: {str(e)}'
        }, status=500)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def record_bill_payment_from_dashboard(request):
    """Record electricity bill payment from performance dashboard"""
    try:
        bill_id = request.POST.get('bill_id')
        payment_amount = request.POST.get('bill_payment_amount')
        payment_date_str = request.POST.get('bill_payment_date')
        notes = request.POST.get('bill_notes', '').strip()
        
        # Validate inputs
        if not bill_id or not payment_amount:
            return JsonResponse({
                'success': False,
                'message': 'Bill ID and amount are required'
            }, status=400)
        
        try:
            payment_amount = Decimal(payment_amount)
            if payment_amount <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Payment amount must be greater than 0'
                }, status=400)
        except:
            return JsonResponse({
                'success': False,
                'message': 'Invalid payment amount'
            }, status=400)
        
        # Parse payment date
        try:
            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
        except:
            return JsonResponse({
                'success': False,
                'message': 'Invalid payment date format'
            }, status=400)
        
        # Get electricity bill
        bill = get_object_or_404(ElectricityBill, id=bill_id)
        
        # Check if payment doesn't exceed remaining
        if payment_amount > bill.remaining_amount():
            return JsonResponse({
                'success': False,
                'message': f'Payment amount exceeds remaining balance of ₹{bill.remaining_amount()}'
            }, status=400)
        
        # Update bill payment
        bill.paid_amount += payment_amount
        
        # Update bill status
        if bill.paid_amount >= bill.bill_amount:
            bill.bill_status = 'paid'
            bill.paid_date = payment_date
        elif bill.paid_amount > 0:
            bill.bill_status = 'partial'
        
        bill.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Bill payment of ₹{payment_amount} recorded successfully'
        })
    
    except Exception as e:
        print(f"Error recording bill payment: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error recording payment: {str(e)}'
        }, status=500)



@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def record_maintenance(request):
    """Record a maintenance expense from the performance dashboard"""
    try:
        building = request.POST.get('building_name') or request.POST.get('building') or ''
        category = request.POST.get('category', 'other')
        amount_raw = request.POST.get('amount') or request.POST.get('expense_amount')
        date_str = request.POST.get('date') or request.POST.get('expense_date')
        description = request.POST.get('description', '').strip()
        is_paid = request.POST.get('is_paid', 'true').lower() in ['true', '1', 'yes', 'on']

        if not building or not amount_raw or not date_str:
            return JsonResponse({'success': False, 'message': 'Building, amount and date are required'}, status=400)

        try:
            amount = Decimal(amount_raw)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Invalid amount'}, status=400)

        try:
            exp_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return JsonResponse({'success': False, 'message': 'Invalid date format'}, status=400)

        expense = MaintenanceExpense.objects.create(
            building_name=building,
            category=category,
            amount=amount,
            date=exp_date,
            description=description,
            is_paid=is_paid,
        )

        return JsonResponse({'success': True, 'message': 'Maintenance expense recorded', 'expense_id': expense.id})

    except Exception as e:
        print(f"Error recording maintenance expense: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)
