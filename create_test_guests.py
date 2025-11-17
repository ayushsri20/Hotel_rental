#!/usr/bin/env python3
"""
Create test guests and assign them to rooms
"""
import os
import sys
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
sys.path.insert(0, '/Users/ayush/hotel_rental/hotel_project')
django.setup()

from rental.models import Room, Guest
from PIL import Image
from io import BytesIO

print("=" * 80)
print("CREATING TEST GUESTS FOR ROOMS")
print("=" * 80)

# Get some available rooms
rooms_to_populate = ['A-01', 'A-02', 'B-01', 'C-01', 'D-01']
created_count = 0

for i, room_number in enumerate(rooms_to_populate, 1):
    try:
        room = Room.objects.get(number=room_number)
        
        # Create guest
        email = f"guest{i}@example.com"
        guest, created = Guest.objects.get_or_create(
            email=email,
            defaults={
                'first_name': f'Guest',
                'last_name': f'{i}',
                'phone': f'999999999{i}',
                'gender': 'M' if i % 2 == 0 else 'F',
                'id_type': 'Aadhaar',
                'id_number': f'12345{i:03d}67890',
                'address': f'Test Address {i}',
                'city': 'Test City',
                'state': 'Test State',
                'country': 'India',
                'zip_code': '123456',
                'room': room,
                'is_active': True,
                'check_in_date': datetime.now(),
                'check_out_date': datetime.now() + timedelta(days=30),
                'lpu_id': f'LPU{i:06d}'
            }
        )
        
        if created:
            print(f"✓ Created: {guest.full_name} in room {room.number}")
            created_count += 1
            
            # Create a simple test image for ID proof
            img = Image.new('RGB', (100, 100), color=('red' if i % 2 == 0 else 'blue'))
            img_io = BytesIO()
            img.save(img_io, 'JPEG')
            img_io.seek(0)
            img_io.name = f'id_proof_{i}.jpg'
            
            guest.id_proof_image.save(f'id_proof_{i}.jpg', img_io, save=False)
            guest.save()
            print(f"  └─ Added ID proof image")
        else:
            print(f"  {guest.full_name} already exists in {room.number}")
    except Room.DoesNotExist:
        print(f"✗ Room {room_number} not found")
    except Exception as e:
        print(f"✗ Error creating guest for {room_number}: {str(e)}")

# Mark rooms as booked if they have guests
print("\n" + "=" * 80)
print("UPDATING ROOM AVAILABILITY")
print("=" * 80)

updated_count = 0
for room in Room.objects.all():
    has_guests = Guest.objects.filter(room=room, is_active=True).exists()
    
    if has_guests and room.is_available:
        room.is_available = False
        room.save()
        updated_count += 1
        print(f"✓ {room.number}: Marked BOOKED")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Guests Created: {created_count}")
print(f"Rooms Updated: {updated_count}")
print(f"Total Active Guests: {Guest.objects.filter(is_active=True).count()}")
print(f"Booked Rooms: {Room.objects.filter(is_available=False).count()}")
print(f"Available Rooms: {Room.objects.filter(is_available=True).count()}")
print("=" * 80)
