"""
Dashboard Metrics API Endpoint
Returns real-time metrics for Analytics Hub auto-refresh
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Sum, F, Case, When, DecimalField, Count
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging

from .models import Building, Room, Guest, MonthlyPayment, PaymentRecord, ElectricityBill, MaintenanceExpense

logger = logging.getLogger(__name__)

def is_admin(user):
    """Check if user is admin"""
    return user.is_staff or user.is_superuser

@login_required(login_url='login')
def dashboard_metrics_api(request):
    """
    Lightweight API endpoint that returns dashboard metrics for real-time updates.
    Returns: Expected Yield, Realized Revenue, Accounts Receivable, Collection Efficiency
    """
    try:
        # Get all rooms
        all_rooms = Room.objects.all()
        total_rooms = all_rooms.count()
        occupied_rooms = Guest.objects.filter(room__isnull=False, is_active=True).count()
        resident_distribution = {building.code: 0 for building in Building.objects.filter(is_active=True)}
        for guest in Guest.objects.filter(is_active=True, room__isnull=False).select_related('room__building'):
            code = guest.room.building.code if guest.room.building else guest.room.number.split('-', 1)[0]
            resident_distribution[code] = resident_distribution.get(code, 0) + 1
        
        # Get current month data
        today = date.today()
        current_month = date(today.year, today.month, 1)
        
        # Calculate metrics using Decimal for precision
        acc_expected_monthly = Decimal('0.00')
        acc_rent_collected = Decimal('0.00')
        acc_electricity_collected = Decimal('0.00')
        acc_electricity_expense = Decimal('0.00')
        acc_pending_amount = Decimal('0.00')
        
        for room in all_rooms:
            if not Guest.objects.filter(room=room, is_active=True).exists():
                continue
            # Get monthly payment for current month
            monthly_payment = MonthlyPayment.objects.filter(
                room=room,
                month=current_month
            ).first()
            
            if monthly_payment:
                monthly_rent = monthly_payment.rent_amount
                bill = monthly_payment.room.electricity_bills.filter(month=current_month).first()
                rent_collected = monthly_payment.paid_amount
                electricity_collected = bill.paid_amount if bill else Decimal('0.00')
                electricity_expense = bill.bill_amount if bill else Decimal('0.00')
                pending = monthly_payment.get_total_remaining()
            else:
                # No payment record, use room's agreed_rent or price
                monthly_rent = room.effective_rent
                rent_collected = Decimal('0.00')
                electricity_collected = Decimal('0.00')
                electricity_expense = Decimal('0.00')
                pending = monthly_rent
            
            # Accumulate totals
            acc_expected_monthly += monthly_payment.get_total_amount_due() if monthly_payment else Decimal(monthly_rent)
            acc_rent_collected += Decimal(rent_collected)
            acc_electricity_collected += Decimal(electricity_collected)
            acc_electricity_expense += Decimal(electricity_expense)
            acc_pending_amount += Decimal(pending)
        
        # Calculate derived metrics
        total_expected_due = acc_expected_monthly
        total_expected_rent = sum(
            room.effective_rent for room in all_rooms
            if Guest.objects.filter(room=room, is_active=True).exists()
        )
        total_expected_rent = Decimal(total_expected_rent)
        total_collected = acc_rent_collected
        total_electricity_collected = acc_electricity_collected
        total_electricity_expense = acc_electricity_expense
        total_pending = acc_pending_amount
        maintenance_expenses = MaintenanceExpense.objects.filter(
            is_paid=True,
            date__year=current_month.year,
            date__month=current_month.month,
        ).aggregate(
            total=Sum('amount', output_field=DecimalField())
        )['total'] or Decimal('0.00')
        total_expenses = maintenance_expenses + total_electricity_expense
        
        # Occupancy rate
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Collection efficiency
        collection_efficiency = (total_collected / total_expected_rent * 100) if total_expected_rent > 0 else 0
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'metrics': {
                'expected_yield': float(total_expected_rent),
                'expected_total_due': float(total_expected_due),
                'electricity_due': float(total_expected_due - total_expected_rent),
                'realized_revenue': float(total_collected),
                'electricity_collected': float(total_electricity_collected),
                'electricity_expense': float(total_electricity_expense),
                'maintenance_expenses': float(maintenance_expenses),
                'accounts_receivable': float(total_pending),
                'collection_efficiency': float(collection_efficiency),
                'total_expenses': float(total_expenses),
                'net_revenue': float(total_collected + total_electricity_collected - total_expenses),
                'occupancy_rate': float(occupancy_rate),
                'resident_distribution': resident_distribution,
            },
            'meta': {
                'total_rooms': total_rooms,
                'occupied_rooms': occupied_rooms,
                'last_updated': datetime.now().isoformat(),
            }
        })
    
    except Exception as e:
        logger.exception("Error in dashboard_metrics_api")
        
        return JsonResponse({
            'success': False,
            'message': f'Error fetching metrics: {str(e)}'
        }, status=500)
