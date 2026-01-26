from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Q, Avg
from .models import Room, Booking, Guest, MonthlyPayment, PaymentRecord, ElectricityBill
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json

import logging
import re

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_staff or user.is_superuser

def home(request):
    return render(request, 'home.html')

def health_check(request):
    return JsonResponse({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            from django.db import connection
            import os
            from django.conf import settings
            
            db_path = settings.DATABASES['default'].get('NAME', 'N/A')
            exists = os.path.exists(db_path) if isinstance(db_path, str) else False
            size = os.path.getsize(db_path) if exists else 0
            cwd = os.getcwd()
            
            try:
                tables = connection.introspection.table_names()
                logger.info(f"DB LOGIN DIAGNOSTIC: Path: {db_path}, Exists: {exists}, Size: {size}, CWD: {cwd}, Tables: {tables}")
            except Exception as diag_err:
                logger.warning(f"DB DIAGNOSTIC FAILED: {diag_err}")
            
            user = authenticate(request, username=username, password=password)
        except Exception as db_err:
            logger.error(f"DB AUTH ERROR: {db_err}")
            migrate_log = "N/A"
            if os.path.exists("migrate_log.txt"):
                try:
                    with open("migrate_log.txt", "r") as f:
                        migrate_log = f.read()
                except:
                    migrate_log = "Error reading log"
            
            diag_str = f"Error: {db_err}. Path: {db_path}, Exists: {exists}, Size: {size}, CWD: {cwd}, Tables: {tables[:5] if 'tables' in locals() else 'N/A'}, Migrate: {migrate_log[-200:] if migrate_log else 'Empty'}"
            return render(request, 'login.html', {'error': f'Database connection error: {diag_str}'})
        
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
    try:
        rooms = Room.objects.all()
        bookings = Booking.objects.all()
        guests = Guest.objects.filter(is_active=True)
        
        # Fetch all active guests and map them to rooms
        active_guests = Guest.objects.filter(is_active=True).select_related('room')
        room_tenants = defaultdict(list)
        for guest in active_guests:
            if guest.room:
                room_tenants[guest.room.id].append(guest)
                
        
        # Enrich rooms with tenant data and calculate status
        for room in rooms:
            tenants = room_tenants.get(room.id, [])
            room.current_tenants = tenants
            
            # Determine Capacity
            # Use database capacity and model properties
            count = len(tenants)
            if count == 0:
                room.occupancy_status = 'empty'
            elif count < room.capacity:
                room.occupancy_status = 'partial'
            else:
                room.occupancy_status = 'full'
                
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
            elif original_name == 'M1': # Handle direct naming if changed in db
                return 'M1'
            else:
                try:
                    # Convert B->1, C->2, D->3, etc.
                    val = ord(original_name) - ord('B') + 1
                    return str(val) if val > 0 else original_name
                except:
                    return original_name
        
        # Apply mapping to building names
        mapped_buildings = [(map_building_name(name), rooms) for name, rooms in sorted_buildings]
        
        # Calculate active stats
        active_rooms_count = rooms.filter(is_available=False).count()
        occupancy_rate = (active_rooms_count / rooms.count() * 100) if rooms.count() > 0 else 0
        
        context = {
            'total_rooms': rooms.count(),
            'available_rooms': rooms.filter(is_available=True).count(),
            'booked_rooms': active_rooms_count,
            'active_rooms_count': active_rooms_count,
            'occupancy_rate': round(occupancy_rate, 1),
            'active_bookings': bookings.filter(is_active=True).count(),
            'total_bookings': bookings.count(),
            'all_bookings': bookings[:5],
            'total_guests': guests.count(),
            'buildings': mapped_buildings,
            'is_admin': request.user.is_staff or request.user.is_superuser,
        }
        
        return render(request, 'dashboard.html', context)
    except Exception as e:
        logger.error(f"Error in dashboard: {e}", exc_info=True)
        return render(request, 'dashboard.html', {'error': str(e), 'total_rooms': 0, 'active_rooms_count': 0})

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
    """Manage guest information with structured data"""
    guests = Guest.objects.all().order_by('-created_at')
    rooms = Room.objects.all().order_by('number')
    
    # Get guest statistics
    guest_stats = {
        'total': guests.count(),
        'active': guests.filter(is_active=True).count(),
        'inactive': guests.filter(is_active=False).count(),
        'with_room': guests.filter(room__isnull=False).count(),
        'without_room': guests.filter(room__isnull=True).count(),
    }
    
    # Generate dynamic building list from existing rooms
    building_prefixes = set()
    building_map = {
        'A': 'M1 Complex',
        'B': 'Building 1',
        'C': 'Building 2',
        'D': 'Building 3',
        'E': 'Building 4',
        'F': 'Building 5',
    }
    
    for room in rooms:
        prefix = room.number.split('-')[0] if '-' in room.number else room.number[0]
        building_prefixes.add(prefix)
    
    # Sort and convert to list with display names
    buildings = sorted([
        {'prefix': prefix, 'name': building_map.get(prefix, f'Building {prefix}')}
        for prefix in building_prefixes
    ], key=lambda x: x['prefix'])
    
    context = {
        'guests': guests,
        'rooms': rooms,
        'available_rooms': [r for r in rooms if r.effective_availability or r.guest_set.filter(is_active=True).exists()], # Include partially filled
        'guest_stats': guest_stats,
        'buildings': buildings,  # Dynamic building list for filters
    }
    
    return render(request, 'manage_guests.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_room(request, room_id):
    try:
        room = get_object_or_404(Room, id=room_id)
        
        # Allow updating room number (unique), room type, price and agreed_rent
        new_number = request.POST.get('number', None)
        if new_number and new_number != room.number:
            # Validate uniqueness
            if Room.objects.filter(number=new_number).exclude(id=room.id).exists():
                return JsonResponse({'success': False, 'message': f'Room number {new_number} already exists'}, status=400)
            room.number = new_number

        room.room_type = request.POST.get('room_type', room.room_type)
        room.capacity = int(request.POST.get('capacity', room.capacity))
        # Support per-room negotiated rent (agreed_rent). If provided, persist it.
        room.price = float(request.POST.get('price', room.price))
        agreed_val = request.POST.get('agreed_rent', None)
        if agreed_val is not None and agreed_val != '':
            try:
                room.agreed_rent = float(agreed_val)
            except ValueError:
                pass
        room.is_available = request.POST.get('is_available') == 'true'
        room.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Room {room.number} updated successfully',
                'room': {
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'price': str(room.price),
                'agreed_rent': str(room.agreed_rent) if room.agreed_rent is not None else None,
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
        capacity = int(request.POST.get('capacity', 1))
        agreed_val = request.POST.get('agreed_rent', None)
        agreed_rent = None
        if agreed_val is not None and agreed_val != '':
            try:
                agreed_rent = float(agreed_val)
            except ValueError:
                agreed_rent = None
        
        if Room.objects.filter(number=room_number).exists():
            return JsonResponse({
                'success': False,
                'message': f'Room {room_number} already exists'
            }, status=400)
        
        room = Room.objects.create(
            number=room_number,
            room_type=room_type,
            price=price,
            capacity=capacity,
            agreed_rent=agreed_rent,
            is_available=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Room {room_number} created successfully',
            'room': {
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                    'price': str(room.price),
                    'agreed_rent': str(room.agreed_rent) if room.agreed_rent is not None else None,
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
        for file_field in ['govt_id_photo', 'college_id_photo', 'document_verification_image']:
            if file_field in request.FILES:
                validate_image_file(request.FILES[file_field])
        
        # Only first_name and last_name are required
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        if not first_name or not last_name:
            return JsonResponse({
                'success': False,
                'message': 'First name and last name are required'
            }, status=400)
        
        check_in = request.POST.get('check_in_date')
        check_out = request.POST.get('check_out_date')
        dob = request.POST.get('date_of_birth')
        
        # Parse dates if provided
        def parse_date(d):
            if not d: return None
            try: return datetime.strptime(d, '%Y-%m-%d').date()
            except: return None

        # Get room and agreed_rent
        room_id = request.POST.get('room_id') or None
        if room_id:
            room = get_object_or_404(Room, id=room_id)
            if room.is_full:
                 return JsonResponse({
                    'success': False,
                    'message': f'Room {room.number} is already full ({room.capacity}/{room.capacity})'
                }, status=400)

        agreed_rent_str = request.POST.get('agreed_rent', '').strip()
        
        guest = Guest.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=request.POST.get('email', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            gender=request.POST.get('gender', 'M'),
            date_of_birth=parse_date(dob),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            country=request.POST.get('country', ''),
            zip_code=request.POST.get('zip_code', ''),
            id_type=request.POST.get('id_type', ''),
            id_number=request.POST.get('id_number', ''),
            college_id=request.POST.get('college_id', ''),
            student_college=request.POST.get('student_college', ''),
            check_in_date=parse_date(check_in),
            check_out_date=parse_date(check_out),
            room_id=room_id,
            notes=request.POST.get('notes', ''),
        )
        
        # Room status update and agreed_rent handling
        if guest.room:
            # Mark as not available only if it reached capacity
            if guest.room.is_full:
                guest.room.is_available = False
            
            # Set agreed_rent on the room if provided (default ₹7000)
            if agreed_rent_str:
                try:
                    guest.room.agreed_rent = float(agreed_rent_str)
                except ValueError:
                    guest.room.agreed_rent = 7000  # Default
            elif not guest.room.agreed_rent:
                guest.room.agreed_rent = 7000  # Default if not set
            guest.room.save()

        if 'govt_id_photo' in request.FILES:
            guest.govt_id_photo = request.FILES['govt_id_photo']
        if 'college_id_photo' in request.FILES:
            guest.college_id_photo = request.FILES['college_id_photo']
        if 'document_verification_image' in request.FILES:
            guest.document_verification_image = request.FILES['document_verification_image']
        guest.save()
        
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
    """
    
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
            'college_id': guest.college_id,
            'student_college': guest.student_college,
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
        
        for file_field in ['govt_id_photo', 'college_id_photo', 'document_verification_image']:
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
        def parse_date(d):
            if not d: return None
            try: return datetime.strptime(d, '%Y-%m-%d').date()
            except: return d # Fallback to original if can't parse

        new_room_id = request.POST.get('room_id') or None
        if new_room_id: new_room_id = int(new_room_id)

        updates = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'email': request.POST.get('email', guest.email).strip(),
            'phone': request.POST.get('phone', '').strip(),
            'gender': request.POST.get('gender', guest.gender),
            'date_of_birth': parse_date(request.POST.get('date_of_birth')),
            'id_type': request.POST.get('id_type', guest.id_type),
            'id_number': request.POST.get('id_number', '').strip(),
            'college_id': request.POST.get('college_id', '').strip(),
            'student_college': request.POST.get('student_college', '').strip(),
            'address': request.POST.get('address', guest.address),
            'city': request.POST.get('city', guest.city),
            'state': request.POST.get('state', guest.state),
            'country': request.POST.get('country', guest.country),
            'zip_code': request.POST.get('zip_code', guest.zip_code),
            'check_in_date': parse_date(request.POST.get('check_in_date')),
            'check_out_date': parse_date(request.POST.get('check_out_date')),
            'notes': request.POST.get('notes', guest.notes),
            'room_id': new_room_id
        }
        
        # Validate updates
        errors = {}
        if not updates['first_name']: errors['first_name'] = 'First name is required'
        if not updates['last_name']: errors['last_name'] = 'Last name is required'
        if updates['email'] and not re.match(r"[^@]+@[^@]+\.[^@]+", updates['email']):
            errors['email'] = 'Invalid email format'
        
        if errors:
            return JsonResponse({'success': False, 'message': 'Validation failed', 'errors': errors}, status=400)
        
        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Handle Room Change
            if guest.room_id != new_room_id:
                # Free old room
                old_room = guest.room
                if old_room:
                    # After this guest leaves, the room will definitely have a free slot
                    old_room.is_available = True
                    old_room.save()
                
                # Occupy new room
                if new_room_id:
                    new_room = Room.objects.get(id=new_room_id)
                    # We check if NEW room is full (excluding the guest themselves if they were already there, 
                    # but here guest.room_id != new_room_id so they weren't)
                    if new_room.is_full:
                         return JsonResponse({
                            'success': False,
                            'message': f'Room {new_room.number} is already full ({new_room.capacity}/{new_room.capacity})'
                        }, status=400)
                    
                    # Update new room status if it becomes full after this guest joins
                    # Note: guest.room_id = new_room_id happens below, so for now current_occupancy doesn't include them
                    if new_room.current_occupancy + 1 >= new_room.capacity:
                        new_room.is_available = False
                        new_room.save()
            
            # Apply updates
            guest.first_name = updates['first_name'] or guest.first_name
            guest.last_name = updates['last_name'] or guest.last_name
            guest.email = updates['email']
            guest.phone = updates['phone'] or guest.phone
            guest.gender = updates['gender']
            guest.date_of_birth = updates['date_of_birth']
            guest.id_type = updates['id_type']
            guest.id_number = updates['id_number']
            guest.college_id = updates['college_id']
            guest.student_college = updates['student_college']
            guest.address = updates['address']
            guest.city = updates['city']
            guest.state = updates['state']
            guest.country = updates['country']
            guest.zip_code = updates['zip_code']
            guest.check_in_date = updates['check_in_date']
            guest.check_out_date = updates['check_out_date']
            guest.room_id = new_room_id
            guest.notes = updates['notes']
            
            # Update images only if provided
            if 'govt_id_photo' in request.FILES:
                guest.govt_id_photo = request.FILES['govt_id_photo']
            if 'college_id_photo' in request.FILES:
                guest.college_id_photo = request.FILES['college_id_photo']
            if 'document_verification_image' in request.FILES:
                guest.document_verification_image = request.FILES['document_verification_image']
            
            # Mark as updated
            guest.updated_at = datetime.now()
            guest.save()
            
            # Audit logging
            logger.info(f"AUDIT - User: {request.user.username} - Updated Guest: {guest.id} ({guest.full_name})")
        
        return JsonResponse({
            'success': True,
            'message': f'✓ Guest {guest.full_name} updated successfully and data synced',
            'guest': {
                'id': guest.id,
                'name': guest.full_name,
                'email': guest.email,
                'phone': guest.phone,
                'college_id': guest.college_id,
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
def checkout_guest(request, guest_id):
    """Mark guest as inactive and free up their room slot."""
    try:
        guest = get_object_or_404(Guest, id=guest_id)
        room = guest.room
        
        with transaction.atomic():
            guest.is_active = False
            # We don't delete the guest or room, just unassign the room for this inactive record
            # Or keep the room but since guest is inactive, current_occupancy (which filters by is_active=True) will drop.
            # To be clear, we usually unassign the room completely during checkout.
            guest.room = None
            guest.save()
            
            if room:
                # Once a guest checks out, the room is definitely not full anymore
                room.is_available = True
                room.save()
                
        return JsonResponse({
            'success': True,
            'message': f'Guest {guest.full_name} checked out successfully. Room {room.number if room else "N/A"} now has a free slot.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_guest(request, guest_id):
    try:
        guest = get_object_or_404(Guest, id=guest_id)
        name = guest.full_name
        
        # Free room and archive
        if guest.room:
            guest.room.is_available = True
            guest.room.save()
            guest.room = None # Remove room assignment
            
        guest.is_active = False
        guest.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Guest {name} archived successfully'
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
        # Default to showing active guests unless specified
        show_archived = request.GET.get('archived') == 'true'
        if show_archived:
            guests = Guest.objects.all().select_related('room').order_by('-created_at')
        else:
            guests = Guest.objects.filter(is_active=True).select_related('room').order_by('-created_at')
            
        guests_data = []
        
        for g in guests:
            guests_data.append({
                'id': g.id,
                'first_name': g.first_name,
                'last_name': g.last_name,
                'full_name': g.full_name,
                'email': g.email,
                'phone': g.phone,
                'gender': g.gender,
                'date_of_birth': g.date_of_birth.strftime('%Y-%m-%d') if g.date_of_birth else None,
                'address': g.address,
                'city': g.city,
                'state': g.state,
                'country': g.country,
                'zip_code': g.zip_code,
                'id_type': g.id_type,
                'id_number': g.id_number,
                'college_id': g.college_id,
                'student_college': g.student_college,
                'check_in_date': g.check_in_date.strftime('%Y-%m-%d') if g.check_in_date else '',
                'check_out_date': g.check_out_date.strftime('%Y-%m-%d') if g.check_out_date else '',
                'notes': g.notes,
                'is_active': g.is_active,
                'created_at': g.created_at.isoformat() if g.created_at else None,
                'room': {
                    'id': g.room.id,
                    'number': g.room.number,
                    'price': str(g.room.price),
                    'agreed_rent': str(g.room.agreed_rent) if g.room.agreed_rent is not None else None
                } if g.room else None,
                'govt_id_photo': g.govt_id_photo.url if g.govt_id_photo else None,
                'college_id_photo': g.college_id_photo.url if g.college_id_photo else None,
            })
        
        return JsonResponse({
            'success': True,
            'guests': guests_data,
            'guest_list': guests_data # For compatibility
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_users(request):
    """View to manage owners/superusers ONLY as per latest requirement"""
    try:
        # User requested to only show users with superuser property
        managed_users = User.objects.filter(is_superuser=True).order_by('-date_joined')
        return render(request, 'manage_users.html', {
            'managed_users': managed_users,
            'is_admin': request.user.is_superuser
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in manage_users view: {e}\n{error_details}")
        return render(request, 'manage_users.html', {
            'managed_users': [],
            'is_admin': request.user.is_superuser,
            'error': f'Unable to load owner accounts: {str(e)}'
        })

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def add_user(request):
    """API to create a new staff user"""
    try:
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_staff = request.POST.get('is_staff') == 'true'

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'message': 'Username already exists'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        user.is_staff = is_staff
        user.save()
        return JsonResponse({'success': True, 'message': '✓ Staff member added successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_user(request, user_id):
    """API to update staff user details"""
    try:
        managed_user = get_object_or_404(User, id=user_id)
        managed_user.first_name = request.POST.get('first_name', managed_user.first_name)
        managed_user.last_name = request.POST.get('last_name', managed_user.last_name)
        managed_user.email = request.POST.get('email', managed_user.email)
        managed_user.is_staff = request.POST.get('is_staff') == 'true'
        managed_user.save()
        return JsonResponse({'success': True, 'message': '✓ User updated successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_user(request, user_id):
    """API to delete staff user"""
    try:
        if request.user.id == user_id:
            return JsonResponse({'success': False, 'message': 'You cannot delete yourself'}, status=400)
        managed_user = get_object_or_404(User, id=user_id)
        managed_user.delete()
        return JsonResponse({'success': True, 'message': '✓ User deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_payments(request):
    """Monthly payment tracking and management"""
    rooms = Room.objects.all().order_by('number')
    payments = MonthlyPayment.objects.select_related('room', 'guest').order_by('-month')
    monthly_payments = MonthlyPayment.objects.select_related('room', 'guest').filter(
        payment_status__in=['pending', 'partial']
    ).order_by('-month')
    
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
        'monthly_payments': monthly_payments,
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
        
        # Determine rent amount: prefer explicit POSTed value, otherwise use room.agreed_rent, then fallback to room.price
        rent_amount_raw = request.POST.get('rent_amount', None)
        rent_amount = None
        if rent_amount_raw is not None and rent_amount_raw != '':
            try:
                rent_amount = float(rent_amount_raw)
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid rent amount'}, status=400)

        
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Room not found'}, status=404)
        
        # If rent_amount not provided, use agreed_rent if set, otherwise room.price
        if not rent_amount or rent_amount <= 0:
            if getattr(room, 'agreed_rent', None) is not None:
                rent_amount = float(room.agreed_rent)
            else:
                rent_amount = float(room.price)

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

        # Parse numeric fields with validation and defaults
        try:
            starting_reading = float(request.POST.get('starting_reading') or 13)  # Default: 13 units
            ending_reading = float(request.POST.get('ending_reading') or (starting_reading + 150))  # Default: +150 units  
            rate_per_unit = float(request.POST.get('rate_per_unit') or 6)  # Default: ₹6/unit
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

        # Get current active guest for the room
        guest = Guest.objects.filter(room=room, is_active=True).first()

        bill, created = ElectricityBill.objects.get_or_create(
            room=room,
            month=month,
            defaults={
                'guest': guest,
                'starting_reading': starting_reading,
                'ending_reading': ending_reading,
                'units_consumed': units_consumed,
                'rate_per_unit': rate_per_unit,
                'bill_amount': bill_amount,
                'due_date': due_date,
            }
        )

        if not created:
            bill.guest = guest
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
    """Display booking form page for creating new guest bookings"""
    return render(request, 'book_room.html')


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
            'price': str(room.price),
            'agreed_rent': str(room.agreed_rent) if room.agreed_rent is not None else None
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
        # When creating monthly payments for the booking range prefer agreed_rent if set
        while current < check_out:
            monthly_payment, created = MonthlyPayment.objects.get_or_create(
                room=room,
                month=current,
                defaults={
                    'guest': guest,
                    'rent_amount': (room.agreed_rent if getattr(room, 'agreed_rent', None) is not None else room.price),
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
def get_room_details(request, room_id):
    """Return basic room details for booking UI (price, agreed_rent, description)"""
    try:
        room = get_object_or_404(Room, id=room_id)
        room_data = {
            'id': room.id,
            'number': room.number,
            'room_type': room.get_room_type_display(),
            'price_per_month': str(room.price),
            'agreed_rent': str(room.agreed_rent) if getattr(room, 'agreed_rent', None) is not None else '',
            'description': getattr(room, 'description', '') if hasattr(room, 'description') else '',
        }
        return JsonResponse({'success': True, 'room': room_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

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


@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def update_payment_record(request, record_id):
    """Update an existing payment record and sync monthly payment total"""
    try:
        record = get_object_or_404(PaymentRecord, id=record_id)
        monthly_payment = record.monthly_payment
        
        old_amount = record.payment_amount
        raw_amount = request.POST.get('payment_amount', str(old_amount))
        new_amount = Decimal(raw_amount)
        
        record.payment_amount = new_amount
        date_str = request.POST.get('payment_date')
        if date_str:
            record.payment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
        record.payment_method = request.POST.get('payment_method', record.payment_method)
        record.notes = request.POST.get('notes', record.notes)
        record.save()
        
        # Recalculate total paid for the month
        total_paid = PaymentRecord.objects.filter(monthly_payment=monthly_payment).aggregate(
            total=Sum('payment_amount'))['total'] or Decimal('0.00')
        
        monthly_payment.paid_amount = total_paid
        # Update status
        if monthly_payment.paid_amount >= monthly_payment.rent_amount:
            monthly_payment.payment_status = 'paid'
        elif monthly_payment.paid_amount > 0:
            monthly_payment.payment_status = 'partial'
        else:
            monthly_payment.payment_status = 'pending'
        monthly_payment.save()
        
        return JsonResponse({'success': True, 'message': 'Payment record updated'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='login')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def delete_payment_record(request, record_id):
    """Delete a payment record and sync monthly payment total"""
    try:
        record = get_object_or_404(PaymentRecord, id=record_id)
        monthly_payment = record.monthly_payment
        record.delete()
        
        # Recalculate
        total_paid = PaymentRecord.objects.filter(monthly_payment=monthly_payment).aggregate(
            total=Sum('payment_amount'))['total'] or Decimal('0.00')
        
        monthly_payment.paid_amount = total_paid
        if monthly_payment.paid_amount >= monthly_payment.rent_amount:
            monthly_payment.payment_status = 'paid'
        elif monthly_payment.paid_amount > 0:
            monthly_payment.payment_status = 'partial'
        else:
            monthly_payment.payment_status = 'pending'
        monthly_payment.save()
        
        return JsonResponse({'success': True, 'message': 'Payment record deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
