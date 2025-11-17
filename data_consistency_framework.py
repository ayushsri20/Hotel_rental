"""
DATA CONSISTENCY FRAMEWORK
===========================
Ensures all tenant details updates propagate correctly throughout the system.
Prevents stale data, inconsistencies, and calculation errors.
"""

from django.db import transaction
from django.core.cache import cache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataConsistencyValidator:
    """
    Validates data consistency and prevents invalid updates.
    Used when updating guest/tenant records.
    """
    
    @staticmethod
    def validate_guest_data(guest, updates):
        """
        Validates guest update data before saving.
        
        Args:
            guest: Guest object
            updates: Dict of fields to update
            
        Returns:
            (is_valid, errors) - Tuple of validation result and error list
        """
        errors = []
        
        # Validate email uniqueness
        if 'email' in updates and updates['email']:
            from rental.models import Guest
            existing = Guest.objects.filter(email=updates['email']).exclude(id=guest.id)
            if existing.exists():
                errors.append(f"Email {updates['email']} already exists")
        
        # Validate phone format
        if 'phone' in updates and updates['phone']:
            phone = updates['phone'].strip()
            if not phone.isdigit() or len(phone) < 10:
                errors.append(f"Invalid phone number: {phone}. Must be at least 10 digits")
        
        # Validate dates
        if 'check_in_date' in updates and 'check_out_date' in updates:
            check_in = updates.get('check_in_date') or guest.check_in_date
            check_out = updates.get('check_out_date') or guest.check_out_date
            
            if check_in and check_out:
                if isinstance(check_in, str):
                    check_in = datetime.strptime(check_in, '%Y-%m-%d').date()
                if isinstance(check_out, str):
                    check_out = datetime.strptime(check_out, '%Y-%m-%d').date()
                
                if check_in >= check_out:
                    errors.append(f"Check-out date ({check_out}) must be after check-in date ({check_in})")
        
        # Validate LPU ID if provided
        if 'lpu_id' in updates and updates['lpu_id']:
            lpu_id = updates['lpu_id'].strip()
            if not lpu_id or len(lpu_id) < 3:
                errors.append(f"Invalid LPU ID: {lpu_id}. Must be at least 3 characters")
        
        # Validate ID number
        if 'id_number' in updates and updates['id_number']:
            id_number = updates['id_number'].strip()
            if not id_number:
                errors.append("ID number cannot be empty if provided")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def validate_payment_data(payment, updates):
        """
        Validates payment record data.
        
        Args:
            payment: MonthlyPayment object
            updates: Dict of fields to update
            
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Validate rent amount
        if 'rent_amount' in updates:
            try:
                amount = float(updates['rent_amount'])
                if amount <= 0:
                    errors.append("Rent amount must be greater than 0")
            except (ValueError, TypeError):
                errors.append(f"Invalid rent amount: {updates['rent_amount']}")
        
        # Validate paid amount doesn't exceed rent
        if 'paid_amount' in updates:
            try:
                paid = float(updates['paid_amount'])
                if paid < 0:
                    errors.append("Paid amount cannot be negative")
                
                rent = float(updates.get('rent_amount', payment.rent_amount))
                if paid > rent:
                    errors.append(f"Paid amount (₹{paid}) cannot exceed rent amount (₹{rent})")
            except (ValueError, TypeError):
                errors.append(f"Invalid paid amount: {updates.get('paid_amount')}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def validate_electricity_bill_data(bill, updates):
        """
        Validates electricity bill data.
        
        Args:
            bill: ElectricityBill object
            updates: Dict of fields to update
            
        Returns:
            (is_valid, errors)
        """
        errors = []
        
        # Validate readings
        for field in ['starting_reading', 'ending_reading']:
            if field in updates:
                try:
                    reading = float(updates[field])
                    if reading < 0:
                        errors.append(f"{field} cannot be negative")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {field}: {updates[field]}")
        
        # Validate ending > starting
        if 'starting_reading' in updates or 'ending_reading' in updates:
            start = float(updates.get('starting_reading', bill.starting_reading))
            end = float(updates.get('ending_reading', bill.ending_reading))
            
            if end <= start:
                errors.append(f"Ending reading ({end}) must be greater than starting reading ({start})")
        
        # Validate rate per unit
        if 'rate_per_unit' in updates:
            try:
                rate = float(updates['rate_per_unit'])
                if rate <= 0:
                    errors.append("Rate per unit must be greater than 0")
            except (ValueError, TypeError):
                errors.append(f"Invalid rate per unit: {updates['rate_per_unit']}")
        
        is_valid = len(errors) == 0
        return is_valid, errors


class DataSyncManager:
    """
    Manages data synchronization across the system.
    Clears caches and ensures updates propagate everywhere.
    """
    
    CACHE_KEYS = {
        'guest': 'guest_{id}',
        'payment': 'payment_{id}',
        'bill': 'bill_{id}',
        'room_tenants': 'room_{id}_tenants',
        'room_payments': 'room_{id}_payments',
        'room_bills': 'room_{id}_bills',
        'payment_history': 'room_{id}_payment_history',
        'bill_history': 'room_{id}_bill_history',
    }
    
    @classmethod
    def invalidate_guest_cache(cls, guest_id, room_id=None):
        """Invalidate guest-related caches after update"""
        logger.info(f"Invalidating cache for guest {guest_id}")
        
        # Invalidate guest cache
        cache_key = cls.CACHE_KEYS['guest'].format(id=guest_id)
        cache.delete(cache_key)
        
        # Invalidate room tenants cache
        if room_id:
            room_cache_key = cls.CACHE_KEYS['room_tenants'].format(id=room_id)
            cache.delete(room_cache_key)
    
    @classmethod
    def invalidate_payment_cache(cls, payment_id, room_id=None):
        """Invalidate payment-related caches after update"""
        logger.info(f"Invalidating cache for payment {payment_id}")
        
        cache_key = cls.CACHE_KEYS['payment'].format(id=payment_id)
        cache.delete(cache_key)
        
        if room_id:
            payment_cache = cls.CACHE_KEYS['room_payments'].format(id=room_id)
            history_cache = cls.CACHE_KEYS['payment_history'].format(id=room_id)
            cache.delete(payment_cache)
            cache.delete(history_cache)
    
    @classmethod
    def invalidate_bill_cache(cls, bill_id, room_id=None):
        """Invalidate bill-related caches after update"""
        logger.info(f"Invalidating cache for bill {bill_id}")
        
        cache_key = cls.CACHE_KEYS['bill'].format(id=bill_id)
        cache.delete(cache_key)
        
        if room_id:
            bill_cache = cls.CACHE_KEYS['room_bills'].format(id=room_id)
            history_cache = cls.CACHE_KEYS['bill_history'].format(id=room_id)
            cache.delete(bill_cache)
            cache.delete(history_cache)


class CalculationVerifier:
    """
    Verifies calculations are correct and consistent.
    Prevents calculation errors in payments and bills.
    """
    
    @staticmethod
    def verify_payment_calculation(monthly_payment):
        """
        Verifies payment record calculations.
        
        Args:
            monthly_payment: MonthlyPayment object
            
        Returns:
            Dict with verification results
        """
        from rental.models import PaymentRecord
        
        # Sum all payment records
        records = PaymentRecord.objects.filter(monthly_payment=monthly_payment)
        calculated_paid = sum(float(r.payment_amount) for r in records)
        
        recorded_paid = float(monthly_payment.paid_amount)
        
        result = {
            'verified': abs(calculated_paid - recorded_paid) < 0.01,  # Allow 1 paise difference
            'calculated_paid': calculated_paid,
            'recorded_paid': recorded_paid,
            'difference': abs(calculated_paid - recorded_paid),
            'rent_amount': float(monthly_payment.rent_amount),
            'remaining': float(monthly_payment.remaining_amount()),
        }
        
        if not result['verified']:
            logger.error(f"Payment calculation mismatch for {monthly_payment.id}: "
                        f"Calculated: ₹{calculated_paid}, Recorded: ₹{recorded_paid}")
        
        return result
    
    @staticmethod
    def verify_bill_calculation(electricity_bill):
        """
        Verifies electricity bill calculation.
        
        Args:
            electricity_bill: ElectricityBill object
            
        Returns:
            Dict with verification results
        """
        # Calculate units consumed
        calculated_units = float(electricity_bill.ending_reading) - float(electricity_bill.starting_reading)
        recorded_units = float(electricity_bill.units_consumed)
        
        # Calculate bill amount
        calculated_bill = calculated_units * float(electricity_bill.rate_per_unit)
        recorded_bill = float(electricity_bill.bill_amount)
        
        result = {
            'verified': (abs(calculated_units - recorded_units) < 0.01 and 
                        abs(calculated_bill - recorded_bill) < 0.01),
            'calculated_units': calculated_units,
            'recorded_units': recorded_units,
            'units_difference': abs(calculated_units - recorded_units),
            'calculated_bill': calculated_bill,
            'recorded_bill': recorded_bill,
            'bill_difference': abs(calculated_bill - recorded_bill),
            'remaining': float(electricity_bill.remaining_amount()),
        }
        
        if not result['verified']:
            logger.error(f"Bill calculation mismatch for {electricity_bill.id}: "
                        f"Units - Calculated: {calculated_units}, Recorded: {recorded_units}; "
                        f"Bill - Calculated: ₹{calculated_bill}, Recorded: ₹{recorded_bill}")
        
        return result
    
    @staticmethod
    def auto_correct_bill_calculations(electricity_bill):
        """
        Automatically corrects bill calculations if they don't match.
        
        Args:
            electricity_bill: ElectricityBill object
        """
        calculated_units = float(electricity_bill.ending_reading) - float(electricity_bill.starting_reading)
        calculated_bill = calculated_units * float(electricity_bill.rate_per_unit)
        
        if abs(calculated_units - float(electricity_bill.units_consumed)) > 0.01:
            logger.warning(f"Auto-correcting units for bill {electricity_bill.id}: "
                          f"{electricity_bill.units_consumed} → {calculated_units}")
            electricity_bill.units_consumed = calculated_units
        
        if abs(calculated_bill - float(electricity_bill.bill_amount)) > 0.01:
            logger.warning(f"Auto-correcting bill amount for bill {electricity_bill.id}: "
                          f"{electricity_bill.bill_amount} → {calculated_bill}")
            electricity_bill.bill_amount = calculated_bill
        
        electricity_bill.save()


class AuditLogger:
    """
    Logs all data updates for audit trail and debugging.
    """
    
    @staticmethod
    @transaction.atomic
    def log_guest_update(guest, old_data, new_data, updated_by=None):
        """Log guest update"""
        from rental.models import Guest
        
        changes = []
        for field, new_value in new_data.items():
            old_value = old_data.get(field)
            if old_value != new_value:
                changes.append(f"{field}: {old_value} → {new_value}")
        
        if changes:
            log_message = f"Guest {guest.id} ({guest.full_name}) updated: {'; '.join(changes)}"
            logger.info(log_message)
            if updated_by:
                logger.info(f"  Updated by: {updated_by.username}")
        
        return len(changes) > 0
    
    @staticmethod
    def log_payment_update(payment, old_data, new_data, updated_by=None):
        """Log payment update"""
        changes = []
        for field, new_value in new_data.items():
            old_value = old_data.get(field)
            if old_value != new_value:
                changes.append(f"{field}: {old_value} → {new_value}")
        
        if changes:
            log_message = f"Payment {payment.id} ({payment.room.number} - {payment.month}) updated: {'; '.join(changes)}"
            logger.info(log_message)
            if updated_by:
                logger.info(f"  Updated by: {updated_by.username}")
        
        return len(changes) > 0
    
    @staticmethod
    def log_bill_update(bill, old_data, new_data, updated_by=None):
        """Log bill update"""
        changes = []
        for field, new_value in new_data.items():
            old_value = old_data.get(field)
            if old_value != new_value:
                changes.append(f"{field}: {old_value} → {new_value}")
        
        if changes:
            log_message = f"Bill {bill.id} ({bill.room.number} - {bill.month}) updated: {'; '.join(changes)}"
            logger.info(log_message)
            if updated_by:
                logger.info(f"  Updated by: {updated_by.username}")
        
        return len(changes) > 0
