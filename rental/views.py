from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Room, Booking, Guest, MonthlyPayment, PaymentRecord, ElectricityBill
from collections import defaultdict
from datetime import datetime, timedelta
import json

def is_admin(user):
    return user.is_staff or user.is_superuser

def home(request):
    return render(request, 'home.html')

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            context = {'error': 'Invalid username or password'}
            return render(request, 'login.html', context)
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='login')
def dashboard(request):
    rooms = Room.objects.all()
    bookings = Booking.objects.all()
    guests = Guest.objects.filter(is_active=True)
    
    # Group rooms by building
    buildings = defaultdict(list)
    for room in rooms:
        building_name = room.number.split('-')[0]
        buildings[building_name].append(room)
    
    # Sort buildings
    sorted_buildings = sorted(buildings.items())
    
    # Map building names: A -> M1, B -> 1, C -> 2, D -> 3, etc.
    def map_building_name(original_name):
        if original_name == 'A':
            return 'M1'
        else:
            # Convert B->1, C->2, D->3, etc.
            return str(ord(original_name) - ord('B') + 1)
    
    # Apply mapping to building names
    mapped_buildings = [(map_building_name(name), rooms) for name, rooms in sorted_buildings]
    
    context = {
        'total_rooms': rooms.count(),
        'available_rooms': rooms.filter(is_available=True).count(),
        'booked_rooms': rooms.filter(is_available=False).count(),
        'active_bookings': bookings.filter(is_active=True).count(),
        'total_bookings': bookings.count(),
        'all_bookings': bookings[:5],
        'total_guests': guests.count(),
        'buildings': mapped_buildings,
        'is_admin': request.user.is_staff or request.user.is_superuser,
    }
    
    return render(request, 'dashboard.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_buildings(request):
    rooms = Room.objects.all().order_by('number')
    
    # Group rooms by building
    buildings = defaultdict(list)
    for room in rooms:
        building_name = room.number.split('-')[0]
        buildings[building_name].append(room)
    
    sorted_buildings = sorted(buildings.items())
    
    # Map building names: A -> M1, B -> 1, C -> 2, D -> 3, etc.
    def map_building_name(original_name):
        if original_name == 'A':
            return 'M1'
        else:
            # Convert B->1, C->2, D->3, etc.
            return str(ord(original_name) - ord('B') + 1)
    
    # Apply mapping to building names
    mapped_buildings = [(map_building_name(name), rooms) for name, rooms in sorted_buildings]
    
    context = {
        'buildings': mapped_buildings,
        'room_types': Room.ROOM_TYPES,
    }
    
    return render(request, 'manage_buildings.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_guests(request):
    guests = Guest.objects.all()
    rooms = Room.objects.all()
    
    context = {
        'guests': guests,
        'rooms': rooms,
    }
    
    return render(request, 'manage_guests.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_room(request, room_id):
    try:
        room = get_object_or_404(Room, id=room_id)
        
        room.room_type = request.POST.get('room_type', room.room_type)
        room.price = float(request.POST.get('price', room.price))
        room.is_available = request.POST.get('is_available') == 'true'
        room.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Room {room.number} updated successfully',
            'room': {
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'price': str(room.price),
                'is_available': room.is_available,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def add_room(request):
    try:
        room_number = request.POST.get('room_number')
        room_type = request.POST.get('room_type')
        price = float(request.POST.get('price', 0))
        
        if Room.objects.filter(number=room_number).exists():
            return JsonResponse({
                'success': False,
                'message': f'Room {room_number} already exists'
            }, status=400)
        
        room = Room.objects.create(
            number=room_number,
            room_type=room_type,
            price=price,
            is_available=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Room {room_number} created successfully',
            'room': {
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'price': str(room.price),
                'is_available': room.is_available,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_room(request, room_id):
    try:
        room = get_object_or_404(Room, id=room_id)
        room_number = room.number
        room.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Room {room_number} deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def add_guest(request):
    try:
        # Validate file size and type before processing
        ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        
        def validate_image_file(file_obj):
            if not file_obj:
                return True
            # Check file extension
            ext = file_obj.name.rsplit('.', 1)[1].lower() if '.' in file_obj.name else ''
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f'Invalid image type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}')
            # Check file size
            if file_obj.size > MAX_FILE_SIZE:
                raise ValueError(f'File size exceeds 5MB limit')
            return True
        
        # Validate all image files
        for file_field in ['id_proof_image', 'lpu_id_photo', 'document_verification_image']:
            if file_field in request.FILES:
                validate_image_file(request.FILES[file_field])
        
        guest = Guest.objects.create(
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            gender=request.POST.get('gender', 'M'),
            date_of_birth=request.POST.get('date_of_birth') or None,
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            country=request.POST.get('country', ''),
            zip_code=request.POST.get('zip_code', ''),
            id_type=request.POST.get('id_type', ''),
            id_number=request.POST.get('id_number', ''),
            lpu_id=request.POST.get('lpu_id', ''),
            check_in_date=request.POST.get('check_in_date') or None,
            check_out_date=request.POST.get('check_out_date') or None,
            room_id=request.POST.get('room_id') or None,
            notes=request.POST.get('notes', ''),
            id_proof_image=request.FILES.get('id_proof_image'),
            lpu_id_photo=request.FILES.get('lpu_id_photo'),
            document_verification_image=request.FILES.get('document_verification_image'),
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Guest {guest.full_name} added successfully',
            'guest': {
                'id': guest.id,
                'full_name': guest.full_name,
                'email': guest.email,
                'phone': guest.phone,
                'room': str(guest.room) if guest.room else 'Unassigned',
            }
        })
    except ValueError as ve:
        return JsonResponse({
            'success': False,
            'message': str(ve)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_guest(request, guest_id):
    """
    Update guest/tenant details with comprehensive validation.
    Ensures all updates propagate correctly throughout the system.
    Clears caches and invalidates derived data.
    """
    from data_consistency_framework import DataConsistencyValidator, DataSyncManager, AuditLogger
    from django.db import transaction
    
    try:
        guest = get_object_or_404(Guest, id=guest_id)
        
        # Store old data for audit
        old_data = {
            'first_name': guest.first_name,
            'last_name': guest.last_name,
            'email': guest.email,
            'phone': guest.phone,
            'gender': guest.gender,
            'id_type': guest.id_type,
            'id_number': guest.id_number,
            'lpu_id': guest.lpu_id,
            'address': guest.address,
            'city': guest.city,
            'state': guest.state,
            'country': guest.country,
            'zip_code': guest.zip_code,
            'check_in_date': guest.check_in_date,
            'check_out_date': guest.check_out_date,
            'notes': guest.notes,
        }
        
        # Validate image files
        ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
        
        def validate_image_file(file_obj):
            if not file_obj:
                return True
            ext = file_obj.name.rsplit('.', 1)[1].lower() if '.' in file_obj.name else ''
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f'Invalid image type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}')
            if file_obj.size > MAX_FILE_SIZE:
                raise ValueError(f'File size exceeds 5MB limit (File size: {file_obj.size / 1024 / 1024:.2f}MB)')
            return True
        
        for file_field in ['id_proof_image', 'lpu_id_photo', 'document_verification_image']:
            if file_field in request.FILES:
                try:
                    validate_image_file(request.FILES[file_field])
                except ValueError as ve:
                    return JsonResponse({
                        'success': False,
                        'message': str(ve),
                        'field': file_field
                    }, status=400)
        
        # Prepare updates
        updates = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'email': request.POST.get('email', guest.email).strip(),
            'phone': request.POST.get('phone', '').strip(),
            'gender': request.POST.get('gender', guest.gender),
            'id_type': request.POST.get('id_type', guest.id_type),
            'id_number': request.POST.get('id_number', '').strip(),
            'lpu_id': request.POST.get('lpu_id', '').strip(),
            'address': request.POST.get('address', guest.address),
            'city': request.POST.get('city', guest.city),
            'state': request.POST.get('state', guest.state),
            'country': request.POST.get('country', guest.country),
            'zip_code': request.POST.get('zip_code', guest.zip_code),
            'check_in_date': request.POST.get('check_in_date', None),
            'check_out_date': request.POST.get('check_out_date', None),
            'notes': request.POST.get('notes', guest.notes),
        }
        
        # Validate updates
        is_valid, errors = DataConsistencyValidator.validate_guest_data(guest, updates)
        if not is_valid:
            return JsonResponse({
                'success': False,
                'message': 'Validation failed',
                'errors': errors
            }, status=400)
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Apply updates
            guest.first_name = updates['first_name'] or guest.first_name
            guest.last_name = updates['last_name'] or guest.last_name
            guest.email = updates['email']
            guest.phone = updates['phone'] or guest.phone
            guest.gender = updates['gender']
            guest.id_type = updates['id_type']
            guest.id_number = updates['id_number']
            guest.lpu_id = updates['lpu_id']
            guest.address = updates['address']
            guest.city = updates['city']
            guest.state = updates['state']
            guest.country = updates['country']
            guest.zip_code = updates['zip_code']
            guest.check_in_date = updates['check_in_date'] or None
            guest.check_out_date = updates['check_out_date'] or None
            guest.notes = updates['notes']
            
            # Update images only if provided
            if 'id_proof_image' in request.FILES:
                guest.id_proof_image = request.FILES['id_proof_image']
            if 'lpu_id_photo' in request.FILES:
                guest.lpu_id_photo = request.FILES['lpu_id_photo']
            if 'document_verification_image' in request.FILES:
                guest.document_verification_image = request.FILES['document_verification_image']
            
            # Mark as updated
            guest.updated_at = datetime.now()
            guest.save()
            
            # Log audit trail
            AuditLogger.log_guest_update(guest, old_data, updates, request.user)
            
            # Invalidate related caches
            DataSyncManager.invalidate_guest_cache(guest.id, guest.room_id)
        
        return JsonResponse({
            'success': True,
            'message': f'✓ Guest {guest.full_name} updated successfully and data synced',
            'guest': {
                'id': guest.id,
                'name': guest.full_name,
                'email': guest.email,
                'phone': guest.phone,
                'lpu_id': guest.lpu_id,
                'check_in': guest.check_in_date.strftime('%Y-%m-%d') if guest.check_in_date else None,
                'check_out': guest.check_out_date.strftime('%Y-%m-%d') if guest.check_out_date else None,
            }
        })
    except ValueError as ve:
        return JsonResponse({
            'success': False,
            'message': f'Validation Error: {str(ve)}'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error updating guest: {str(e)}'
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_guest(request, guest_id):
    try:
        guest = get_object_or_404(Guest, id=guest_id)
        name = guest.full_name
        guest.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Guest {name} deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_guests(request):
    try:
        guests = Guest.objects.all().select_related('room').order_by('-created_at')
        guests_data = []
        
        for guest in guests:
            guests_data.append({
                'id': guest.id,
                'first_name': guest.first_name,
                'last_name': guest.last_name,
                'full_name': guest.full_name,
                'email': guest.email,
                'phone': guest.phone,
                'gender': guest.gender,
                'date_of_birth': guest.date_of_birth,
                'address': guest.address,
                'city': guest.city,
                'state': guest.state,
                'country': guest.country,
                'zip_code': guest.zip_code,
                'id_type': guest.id_type,
                'id_number': guest.id_number,
                'check_in_date': guest.check_in_date,
                'check_out_date': guest.check_out_date,
                'room': {
                    'id': guest.room.id,
                    'number': guest.room.number,
                    'price': str(guest.room.price)
                } if guest.room else None,
                'notes': guest.notes,
                'is_active': guest.is_active,
                'created_at': guest.created_at.isoformat() if guest.created_at else None,
            })
        
        return JsonResponse({
            'success': True,
            'guests': guests_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

# Payment Management Views
@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_payments(request):
    """Monthly payment tracking and management"""
    rooms = Room.objects.all().order_by('number')
    payments = MonthlyPayment.objects.select_related('room', 'guest').order_by('-month')
    
    # Get payment status summary
    payment_stats = {
        'pending': payments.filter(payment_status='pending').count(),
        'partial': payments.filter(payment_status='partial').count(),
        'paid': payments.filter(payment_status='paid').count(),
        'overdue': payments.filter(payment_status='overdue').count(),
        'total_pending_amount': sum(p.remaining_amount() for p in payments.filter(payment_status__in=['pending', 'partial', 'overdue'])),
    }
    
    context = {
        'rooms': rooms,
        'payments': payments[:100],
        'payment_stats': payment_stats,
    }
    
    return render(request, 'manage_payments.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_electricity_bills(request):
    """Electricity bill tracking and management"""
    rooms = Room.objects.all().order_by('number')
    bills = ElectricityBill.objects.select_related('room', 'guest').order_by('-month')
    
    # Get bill status summary
    bill_stats = {
        'pending': bills.filter(bill_status='pending').count(),
        'paid': bills.filter(bill_status='paid').count(),
        'overdue': bills.filter(bill_status='overdue').count(),
        'total_pending_amount': sum(b.remaining_amount() for b in bills.filter(bill_status__in=['pending', 'overdue'])),
    }
    
    context = {
        'rooms': rooms,
        'bills': bills[:100],
        'bill_stats': bill_stats,
    }
    
    return render(request, 'manage_electricity_bills.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def create_monthly_payment(request):
    """Create monthly payment record for a room"""
    try:
        room_id = request.POST.get('room_id')
        month_str = request.POST.get('month')
        
        if not room_id or not room_id.strip():
            return JsonResponse({'success': False, 'message': 'Room ID is required'}, status=400)
        if not month_str or not month_str.strip():
            return JsonResponse({'success': False, 'message': 'Month is required'}, status=400)
        
        try:
            rent_amount = float(request.POST.get('rent_amount', 0))
            if rent_amount <= 0:
                return JsonResponse({'success': False, 'message': 'Rent amount must be greater than 0'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid rent amount'}, status=400)
        
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Room not found'}, status=404)
        
        # Parse month - handle both YYYY-MM-DD and YYYY-MM formats
        try:
            if len(month_str) == 10 and month_str[4] == '-' and month_str[7] == '-':
                # YYYY-MM-DD format
                month = datetime.strptime(month_str, '%Y-%m-%d').date()
            elif len(month_str) == 7 and month_str[4] == '-':
                # YYYY-MM format
                month = datetime.strptime(month_str, '%Y-%m').date()
            else:
                return JsonResponse({'success': False, 'message': f'Invalid month format: {month_str}. Use YYYY-MM or YYYY-MM-DD'}, status=400)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': f'Error parsing month: {str(e)}'}, status=400)
        
        payment, created = MonthlyPayment.objects.get_or_create(
            room=room,
            month=month,
            defaults={'rent_amount': rent_amount}
        )
        
        if not created:
            payment.rent_amount = rent_amount
            payment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Payment record {"created" if created else "updated"} for {room.number}',
            'payment': {
                'id': payment.id,
                'room': room.number,
                'month': month.strftime('%B %Y'),
                'rent_amount': str(payment.rent_amount),
                'paid_amount': str(payment.paid_amount),
                'status': payment.payment_status,
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error creating payment: {str(e)}'
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def record_payment(request):
    """Record a payment against monthly rent"""
    try:
        payment_id = request.POST.get('payment_id')
        if not payment_id:
            return JsonResponse({'success': False, 'message': 'Payment ID is required'}, status=400)
        
        # Validate and parse amount
        try:
            payment_amount = float(request.POST.get('payment_amount', 0))
            if payment_amount <= 0:
                return JsonResponse({'success': False, 'message': 'Payment amount must be greater than 0'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid payment amount'}, status=400)
        
        # Validate and parse date
        payment_date_str = request.POST.get('payment_date')
        if not payment_date_str:
            return JsonResponse({'success': False, 'message': 'Payment date is required'}, status=400)
        
        try:
            from datetime import datetime as dt
            payment_date = dt.strptime(payment_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'message': f'Invalid date format. Please use YYYY-MM-DD format. Received: {payment_date_str}'}, status=400)
        
        payment_method = request.POST.get('payment_method', 'cash')
        reference = request.POST.get('reference_number', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        monthly_payment = get_object_or_404(MonthlyPayment, id=payment_id)
        
        # Create payment record
        record = PaymentRecord.objects.create(
            monthly_payment=monthly_payment,
            payment_date=payment_date,
            payment_amount=payment_amount,
            payment_method=payment_method,
            reference_number=reference,
            notes=notes,
            created_by=request.user
        )
        
        # Update monthly payment
        monthly_payment.paid_amount += payment_amount
        if monthly_payment.paid_amount >= monthly_payment.rent_amount:
            monthly_payment.payment_status = 'paid'
            monthly_payment.paid_date = payment_date
        elif monthly_payment.paid_amount > 0:
            monthly_payment.payment_status = 'partial'
        
        monthly_payment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Payment of ₹{payment_amount:.2f} recorded successfully on {payment_date.strftime("%d-%m-%Y")}',
            'payment': {
                'id': monthly_payment.id,
                'paid_amount': str(monthly_payment.paid_amount),
                'status': monthly_payment.payment_status,
                'remaining': str(monthly_payment.remaining_amount()),
            }
        })
    except MonthlyPayment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Payment record not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error recording payment: {str(e)}'
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def create_electricity_bill(request):
    """Create electricity bill for a room"""
    try:
        room_id = request.POST.get('room_id')
        month_str = request.POST.get('month')
        due_date_str = request.POST.get('due_date')

        # Validate required fields
        if not room_id:
            return JsonResponse({'success': False, 'message': 'Room ID is required'}, status=400)
        if not month_str:
            return JsonResponse({'success': False, 'message': 'Month is required (YYYY-MM or YYYY-MM-DD)'}, status=400)

        # Parse numeric fields with validation
        try:
            starting_reading = float(request.POST.get('starting_reading', 0))
            ending_reading = float(request.POST.get('ending_reading', 0))
            rate_per_unit = float(request.POST.get('rate_per_unit', 0))
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Invalid numeric input for readings or rate'}, status=400)

        if ending_reading < starting_reading:
            return JsonResponse({'success': False, 'message': 'Ending reading must be greater than or equal to starting reading'}, status=400)
        if rate_per_unit <= 0:
            return JsonResponse({'success': False, 'message': 'Rate per unit must be greater than 0'}, status=400)

        # Get room
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Room not found'}, status=404)

        # Parse month - accept YYYY-MM-DD or YYYY-MM
        try:
            if len(month_str) == 10 and month_str[4] == '-' and month_str[7] == '-':
                month = datetime.strptime(month_str, '%Y-%m-%d').date()
            elif len(month_str) == 7 and month_str[4] == '-':
                month = datetime.strptime(month_str, '%Y-%m').date()
            else:
                return JsonResponse({'success': False, 'message': f'Invalid month format: {month_str}. Use YYYY-MM or YYYY-MM-DD'}, status=400)
        except ValueError as e:
            return JsonResponse({'success': False, 'message': f'Error parsing month: {str(e)}'}, status=400)

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid due date format. Use YYYY-MM-DD'}, status=400)

        units_consumed = ending_reading - starting_reading
        bill_amount = units_consumed * rate_per_unit

        bill, created = ElectricityBill.objects.get_or_create(
            room=room,
            month=month,
            defaults={
                'starting_reading': starting_reading,
                'ending_reading': ending_reading,
                'units_consumed': units_consumed,
                'rate_per_unit': rate_per_unit,
                'bill_amount': bill_amount,
                'due_date': due_date,
            }
        )

        if not created:
            bill.starting_reading = starting_reading
            bill.ending_reading = ending_reading
            bill.units_consumed = units_consumed
            bill.rate_per_unit = rate_per_unit
            bill.bill_amount = bill_amount
            bill.due_date = due_date
            bill.save()

        return JsonResponse({
            'success': True,
            'message': f'Electricity bill created for {room.number}',
            'bill': {
                'id': bill.id,
                'room': room.number,
                'month': month.strftime('%B %Y'),
                'units': str(bill.units_consumed),
                'bill_amount': str(bill.bill_amount),
                'status': bill.bill_status,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def record_electricity_payment(request):
    """Record electricity bill payment"""
    try:
        bill_id = request.POST.get('bill_id')
        paid_amount = float(request.POST.get('paid_amount', 0))
        paid_date = request.POST.get('paid_date')
        
        bill = get_object_or_404(ElectricityBill, id=bill_id)
        bill.paid_amount += paid_amount
        
        if bill.paid_amount >= bill.bill_amount:
            bill.bill_status = 'paid'
            bill.paid_date = paid_date
        
        bill.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Electricity payment of ₹{paid_amount} recorded',
            'bill': {
                'id': bill.id,
                'paid_amount': str(bill.paid_amount),
                'status': bill.bill_status,
                'remaining': str(bill.remaining_amount()),
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_payment_history(request, room_id):
    """Get payment history for a room"""
    try:
        room = get_object_or_404(Room, id=room_id)
        payments = MonthlyPayment.objects.filter(room=room).order_by('-month')
        
        history = []
        for payment in payments:
            records = PaymentRecord.objects.filter(monthly_payment=payment).order_by('-payment_date')
            history.append({
                'id': payment.id,
                'month': payment.month.strftime('%B %Y'),
                'rent_amount': str(payment.rent_amount),
                'paid_amount': str(payment.paid_amount),
                'remaining': str(payment.remaining_amount()),
                'status': payment.payment_status,
                'paid_date': payment.paid_date.strftime('%Y-%m-%d') if payment.paid_date else None,
                'records': [{
                    'date': r.payment_date.strftime('%Y-%m-%d'),
                    'amount': str(r.payment_amount),
                    'method': r.get_payment_method_display(),
                    'ref': r.reference_number,
                } for r in records]
            })
        
        return JsonResponse({
            'success': True,
            'room': room.number,
            'history': history
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


# =====================
# BOOKING MANAGEMENT
# =====================

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def booking_page(request):
    """Display booking form page"""
    return render(request, 'book_rooom.html')


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_available_rooms(request):
    """Get list of available rooms"""
    try:
        # Get only available rooms
        available_rooms = Room.objects.filter(is_available=True)
        
        rooms_data = [{
            'id': room.id,
            'number': room.number,
            'room_type': room.get_room_type_display(),
            'price': str(room.price)
        } for room in available_rooms]
        
        return JsonResponse({
            'success': True,
            'rooms': rooms_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def submit_booking(request):
    """Submit booking with guest information"""
    try:
        from dateutil.relativedelta import relativedelta
        
        # Parse form data
        room_id = request.POST.get('room_id')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', 'M')
        date_of_birth = request.POST.get('date_of_birth', None)
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        country = request.POST.get('country', 'India').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        id_type = request.POST.get('id_type', '').strip()
        id_number = request.POST.get('id_number', '').strip()
        check_in_date = request.POST.get('check_in_date')
        check_out_date = request.POST.get('check_out_date')
        notes = request.POST.get('notes', '').strip()
        
        # Validate required fields
        if not all([room_id, first_name, last_name, email, phone, id_type, id_number, check_in_date, check_out_date]):
            return JsonResponse({
                'success': False,
                'message': 'Please fill in all required fields'
            }, status=400)
        
        # Get room
        room = get_object_or_404(Room, id=room_id)
        if not room.is_available:
            return JsonResponse({
                'success': False,
                'message': 'This room is no longer available'
            }, status=400)
        
        # Parse dates
        try:
            check_in = datetime.strptime(check_in_date, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid date format'
            }, status=400)
        
        # Validate dates
        if check_in >= check_out:
            return JsonResponse({
                'success': False,
                'message': 'Check-out date must be after check-in date'
            }, status=400)
        
        # Check if email already exists
        existing_guest = Guest.objects.filter(email=email).first()
        if existing_guest:
            guest = existing_guest
            # Update guest information
            guest.first_name = first_name
            guest.last_name = last_name
            guest.phone = phone
            guest.gender = gender
            guest.date_of_birth = date_of_birth if date_of_birth else guest.date_of_birth
            guest.address = address
            guest.city = city
            guest.state = state
            guest.country = country
            guest.zip_code = zip_code
            guest.id_type = id_type
            guest.id_number = id_number
            guest.notes = notes
        else:
            # Create new guest
            guest = Guest(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                gender=gender,
                date_of_birth=date_of_birth if date_of_birth else None,
                address=address,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                id_type=id_type,
                id_number=id_number,
                notes=notes,
                is_active=True
            )
        
        guest.check_in_date = check_in
        guest.check_out_date = check_out
        guest.room = room
        guest.save()
        
        # Create or update booking
        booking = Booking.objects.create(
            room=room,
            customer_name=f"{first_name} {last_name}",
            check_in=check_in,
            check_out=check_out,
            created_by=request.user if request.user.is_authenticated else None,
            is_active=True
        )
        
        # Create monthly payment record if needed
        current = check_in.replace(day=1)
        while current < check_out:
            monthly_payment, created = MonthlyPayment.objects.get_or_create(
                room=room,
                month=current,
                defaults={
                    'guest': guest,
                    'rent_amount': room.price,
                    'paid_amount': 0,
                    'payment_status': 'pending',
                }
            )
            if created:
                monthly_payment.guest = guest
                monthly_payment.save()
            
            current = current + relativedelta(months=1)
        
        console_log_data = {
            'action': 'booking_created',
            'guest': f"{guest.first_name} {guest.last_name}",
            'room': room.number,
            'check_in': check_in.strftime('%Y-%m-%d'),
            'check_out': check_out.strftime('%Y-%m-%d'),
            'booking_id': booking.id
        }
        
        print(f"✓ Booking created successfully: {json.dumps(console_log_data, indent=2)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Booking completed successfully',
            'booking_id': booking.id,
            'guest_id': guest.id
        })
        
    except Exception as e:
        print(f"✗ Booking error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error creating booking: {str(e)}'
        }, status=400)


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_room_tenants(request, room_id):
    """Get current and past tenants for a room"""
    try:
        room = get_object_or_404(Room, id=room_id)
        
        # Get active guests in this room
        guests = Guest.objects.filter(room=room, is_active=True).order_by('-check_in_date')
        
        guests_data = []
        for guest in guests:
            guests_data.append({
                'id': guest.id,
                'name': guest.full_name,
                'email': guest.email,
                'phone': guest.phone,
                'check_in': guest.check_in_date.strftime('%Y-%m-%d') if guest.check_in_date else None,
                'check_out': guest.check_out_date.strftime('%Y-%m-%d') if guest.check_out_date else None,
                'gender': guest.get_gender_display() if hasattr(guest, 'get_gender_display') else guest.gender,
                'id_type': guest.id_type,
                'id_number': guest.id_number,
                'address': guest.address,
                'city': guest.city,
                'state': guest.state,
                'country': guest.country,
                'zip_code': guest.zip_code,
                'notes': guest.notes,
                'lpu_id': guest.lpu_id if hasattr(guest, 'lpu_id') else '',
                'id_proof_image': guest.id_proof_image.url if guest.id_proof_image else None,
                'lpu_id_photo': guest.lpu_id_photo.url if guest.lpu_id_photo else None,
                'document_verification_image': guest.document_verification_image.url if guest.document_verification_image else None
            })
        
        return JsonResponse({
            'success': True,
            'room': room.number,
            'tenants': guests_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def get_electricity_history(request, room_id):
    """Get electricity bill history for a room"""
    try:
        room = get_object_or_404(Room, id=room_id)
        bills = ElectricityBill.objects.filter(room=room).order_by('-month')
        
        history = []
        for bill in bills:
            history.append({
                'id': bill.id,
                'month': bill.month.strftime('%B %Y'),
                'units': str(bill.units_consumed),
                'rate': str(bill.rate_per_unit),
                'bill_amount': str(bill.bill_amount),
                'paid_amount': str(bill.paid_amount),
                'remaining': str(bill.remaining_amount()),
                'status': bill.bill_status,
                'due_date': bill.due_date.strftime('%Y-%m-%d'),
                'paid_date': bill.paid_date.strftime('%Y-%m-%d') if bill.paid_date else None,
            })
        
        return JsonResponse({
            'success': True,
            'room': room.number,
            'history': history
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
