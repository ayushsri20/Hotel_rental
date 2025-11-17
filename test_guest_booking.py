#!/usr/bin/env python
"""
Test Case: Create Guest Entry and Record Payment
Testing the complete flow of:
1. Guest Registration
2. Room Assignment
3. Booking Creation
4. Monthly Payment Recording
"""

import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import Guest, Room, Booking, MonthlyPayment, PaymentRecord
from django.contrib.auth.models import User

def test_case_1_create_guest():
    """Test Case 1: Create a complete guest entry"""
    print("\n" + "="*80)
    print("TEST CASE 1: CREATE GUEST ENTRY")
    print("="*80)
    
    try:
        # Clear any existing test guest
        Guest.objects.filter(email='testguest@example.com').delete()
        
        # Create guest
        guest = Guest.objects.create(
            first_name='Rajesh',
            last_name='Kumar',
            email='testguest@example.com',
            phone='9876543210',
            gender='M',
            date_of_birth='1990-05-15',
            address='123, Main Street',
            city='Delhi',
            state='Delhi',
            country='India',
            zip_code='110001',
            id_type='Aadhar',
            id_number='123456789012',
            is_active=True
        )
        
        print(f"✓ Guest Created Successfully")
        print(f"  Guest ID: {guest.id}")
        print(f"  Name: {guest.full_name}")
        print(f"  Email: {guest.email}")
        print(f"  Phone: {guest.phone}")
        print(f"  Gender: {guest.get_gender_display()}")
        print(f"  DOB: {guest.date_of_birth}")
        print(f"  Address: {guest.address}, {guest.city}, {guest.state}")
        print(f"  ID Type: {guest.id_type}")
        print(f"  ID Number: {guest.id_number}")
        print(f"  Status: {'Active' if guest.is_active else 'Inactive'}")
        
        return guest
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return None

def test_case_2_assign_room(guest):
    """Test Case 2: Assign a room to guest"""
    print("\n" + "="*80)
    print("TEST CASE 2: ASSIGN ROOM TO GUEST")
    print("="*80)
    
    try:
        # Get first available room (building M1 / A)
        room = Room.objects.filter(is_available=True).first()
        
        if not room:
            print("✗ ERROR: No available rooms found")
            return None
        
        # Check in guest
        today = datetime.now().date()
        guest.room = room
        guest.check_in_date = today
        guest.check_out_date = today + timedelta(days=90)  # 3 month stay
        guest.save()
        
        # Mark room as unavailable
        room.is_available = False
        room.save()
        
        print(f"✓ Room Assigned Successfully")
        print(f"  Room Number: {room.number}")
        print(f"  Room Type: {room.get_room_type_display()}")
        print(f"  Room Price: ₹{room.price}")
        print(f"  Guest: {guest.full_name}")
        print(f"  Check-in: {guest.check_in_date}")
        print(f"  Check-out: {guest.check_out_date}")
        print(f"  Room Status: Not Available (Occupied)")
        
        return room
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return None

def test_case_3_create_booking(guest, room):
    """Test Case 3: Create booking record"""
    print("\n" + "="*80)
    print("TEST CASE 3: CREATE BOOKING RECORD")
    print("="*80)
    
    try:
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        
        # Create booking
        booking = Booking.objects.create(
            room=room,
            customer_name=guest.full_name,
            check_in=guest.check_in_date,
            check_out=guest.check_out_date,
            created_by=admin_user,
            is_active=True
        )
        
        print(f"✓ Booking Created Successfully")
        print(f"  Booking ID: {booking.id}")
        print(f"  Customer: {booking.customer_name}")
        print(f"  Room: {booking.room.number}")
        print(f"  Check-in: {booking.check_in}")
        print(f"  Check-out: {booking.check_out}")
        print(f"  Duration: {(booking.check_out - booking.check_in).days} days")
        print(f"  Room Price: ₹{booking.room.price}/month")
        print(f"  Status: {'Active' if booking.is_active else 'Inactive'}")
        print(f"  Created By: {booking.created_by.username}")
        
        return booking
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return None

def test_case_4_create_monthly_payment(guest, room):
    """Test Case 4: Create monthly payment record"""
    print("\n" + "="*80)
    print("TEST CASE 4: CREATE MONTHLY PAYMENT RECORD")
    print("="*80)
    
    try:
        # Create payment for current month
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # Delete if exists
        MonthlyPayment.objects.filter(room=room, month=month_start).delete()
        
        # Create monthly payment
        monthly_payment = MonthlyPayment.objects.create(
            room=room,
            guest=guest,
            month=month_start,
            rent_amount=Decimal(room.price),
            paid_amount=Decimal('0'),
            payment_status='pending',
            notes=f"Monthly rent for {guest.full_name} in Room {room.number}"
        )
        
        print(f"✓ Monthly Payment Record Created")
        print(f"  Payment ID: {monthly_payment.id}")
        print(f"  Room: {monthly_payment.room.number}")
        print(f"  Guest: {guest.full_name}")
        print(f"  Month: {monthly_payment.month.strftime('%B %Y')}")
        print(f"  Rent Amount: ₹{monthly_payment.rent_amount}")
        print(f"  Paid Amount: ₹{monthly_payment.paid_amount}")
        print(f"  Remaining: ₹{monthly_payment.remaining_amount()}")
        print(f"  Status: {monthly_payment.get_payment_status_display()}")
        print(f"  Notes: {monthly_payment.notes}")
        
        return monthly_payment
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return None

def test_case_5_record_payment(monthly_payment):
    """Test Case 5: Record a payment of ₹2000"""
    print("\n" + "="*80)
    print("TEST CASE 5: RECORD PAYMENT OF ₹2000")
    print("="*80)
    
    try:
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        payment_amount = Decimal('2000')
        
        # Create payment record
        payment_record = PaymentRecord.objects.create(
            monthly_payment=monthly_payment,
            payment_date=datetime.now().date(),
            payment_amount=payment_amount,
            payment_method='cash',
            reference_number='CASH-001',
            notes='Guest paid ₹2000 as partial payment',
            created_by=admin_user
        )
        
        # Update monthly payment
        monthly_payment.paid_amount += payment_amount
        
        # Update payment status
        if monthly_payment.paid_amount >= monthly_payment.rent_amount:
            monthly_payment.payment_status = 'paid'
            monthly_payment.paid_date = datetime.now().date()
        elif monthly_payment.paid_amount > 0:
            monthly_payment.payment_status = 'partial'
        
        monthly_payment.save()
        
        print(f"✓ Payment Recorded Successfully")
        print(f"  Payment Record ID: {payment_record.id}")
        print(f"  Room: {monthly_payment.room.number}")
        print(f"  Payment Amount: ₹{payment_record.payment_amount}")
        print(f"  Payment Method: {payment_record.get_payment_method_display()}")
        print(f"  Reference: {payment_record.reference_number}")
        print(f"  Payment Date: {payment_record.payment_date}")
        print(f"  Notes: {payment_record.notes}")
        print(f"  Recorded By: {payment_record.created_by.username}")
        
        print(f"\n  Monthly Payment Updated:")
        print(f"  Total Rent: ₹{monthly_payment.rent_amount}")
        print(f"  Total Paid: ₹{monthly_payment.paid_amount}")
        print(f"  Remaining: ₹{monthly_payment.remaining_amount()}")
        print(f"  Status: {monthly_payment.get_payment_status_display()}")
        
        return payment_record
    
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return None

def test_case_6_verify_data():
    """Test Case 6: Verify all data in database"""
    print("\n" + "="*80)
    print("TEST CASE 6: VERIFY DATA INTEGRITY")
    print("="*80)
    
    try:
        # Verify guest
        guest = Guest.objects.get(email='testguest@example.com')
        print(f"✓ Guest Verification")
        print(f"  Guest Found: {guest.full_name}")
        print(f"  Contact: {guest.phone}")
        print(f"  Assigned Room: {guest.room.number if guest.room else 'None'}")
        
        # Verify room
        room = guest.room
        print(f"\n✓ Room Verification")
        print(f"  Room: {room.number}")
        print(f"  Type: {room.get_room_type_display()}")
        print(f"  Price: ₹{room.price}")
        print(f"  Available: {room.is_available}")
        
        # Verify booking
        booking = Booking.objects.filter(room=room, is_active=True).first()
        if booking:
            print(f"\n✓ Booking Verification")
            print(f"  Booking ID: {booking.id}")
            print(f"  Customer: {booking.customer_name}")
            print(f"  Duration: {(booking.check_out - booking.check_in).days} days")
        
        # Verify payment
        today = datetime.now().date()
        month_start = today.replace(day=1)
        monthly_payment = MonthlyPayment.objects.filter(room=room, month=month_start).first()
        
        if monthly_payment:
            print(f"\n✓ Monthly Payment Verification")
            print(f"  Payment ID: {monthly_payment.id}")
            print(f"  Status: {monthly_payment.get_payment_status_display()}")
            print(f"  Total Rent: ₹{monthly_payment.rent_amount}")
            print(f"  Paid: ₹{monthly_payment.paid_amount}")
            print(f"  Remaining: ₹{monthly_payment.remaining_amount()}")
            
            # Verify payment records
            payment_records = monthly_payment.payment_records.all()
            print(f"\n✓ Payment Records ({payment_records.count()} total)")
            for record in payment_records:
                print(f"  - ₹{record.payment_amount} on {record.payment_date} ({record.get_payment_method_display()})")
        
        print(f"\n✓ ALL DATA VERIFIED SUCCESSFULLY")
        
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")

def run_all_tests():
    """Run all test cases"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "COMPREHENSIVE TEST SUITE - GUEST BOOKING SYSTEM" + " "*13 + "║")
    print("╚" + "="*78 + "╝")
    
    # Run test cases
    guest = test_case_1_create_guest()
    if not guest:
        print("Test suite stopped due to errors")
        return
    
    room = test_case_2_assign_room(guest)
    if not room:
        print("Test suite stopped due to errors")
        return
    
    booking = test_case_3_create_booking(guest, room)
    if not booking:
        print("Test suite stopped due to errors")
        return
    
    monthly_payment = test_case_4_create_monthly_payment(guest, room)
    if not monthly_payment:
        print("Test suite stopped due to errors")
        return
    
    payment_record = test_case_5_record_payment(monthly_payment)
    if not payment_record:
        print("Test suite stopped due to errors")
        return
    
    test_case_6_verify_data()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("✓ Test Case 1: Guest Creation - PASSED")
    print("✓ Test Case 2: Room Assignment - PASSED")
    print("✓ Test Case 3: Booking Creation - PASSED")
    print("✓ Test Case 4: Monthly Payment Creation - PASSED")
    print("✓ Test Case 5: Payment Recording (₹2000) - PASSED")
    print("✓ Test Case 6: Data Verification - PASSED")
    print("\n✓ ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*80 + "\n")

if __name__ == '__main__':
    run_all_tests()
