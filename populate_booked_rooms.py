#!/usr/bin/env python3
"""
Populate ALL booked rooms with tenant data
Ensures every booked room (is_available=False) has at least one tenant
"""
import os
import sys
import django
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
sys.path.insert(0, '/Users/ayush/hotel_rental/hotel_project')
django.setup()

from rental.models import Room, Guest

print("=" * 80)
print("POPULATING ALL BOOKED ROOMS WITH TENANT DATA")
print("=" * 80)

# Sample first and last names
first_names = ['Rajesh', 'Priya', 'Amit', 'Neha', 'Vikram', 'Anjali', 'Arjun', 'Divya', 
               'Rohan', 'Pooja', 'Nitin', 'Shreya', 'Varun', 'Isha', 'Aditya']
last_names = ['Kumar', 'Sharma', 'Patel', 'Singh', 'Gupta', 'Verma', 'Nair', 'Rao',
              'Bhat', 'Desai', 'Chopra', 'Joshi', 'Reddy', 'Iyer', 'Malhotra']

# Sample cities
cities = ['Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Pune', 'Chennai', 'Kolkata', 'Indore']
states = ['Delhi', 'Maharashtra', 'Karnataka', 'Telangana', 'Maharashtra', 'Tamil Nadu', 'West Bengal', 'Madhya Pradesh']

def create_test_image(name):
    """Create a simple colored image"""
    colors = [
        (220, 20, 60),    # Crimson
        (30, 144, 255),   # Dodger Blue
        (34, 139, 34),    # Forest Green
        (255, 140, 0),    # Dark Orange
        (75, 0, 130),     # Indigo
        (220, 20, 60),    # Crimson
    ]
    color = random.choice(colors)
    
    img = Image.new('RGB', (100, 100), color=color)
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    img_io.name = f'{name}.jpg'
    return img_io

print("\n" + "=" * 80)
print("ANALYZING BOOKED ROOMS")
print("=" * 80)

booked_rooms = Room.objects.filter(is_available=False)
print(f"\nTotal booked rooms: {booked_rooms.count()}")

rooms_without_tenants = []
rooms_with_tenants = []

for room in booked_rooms:
    guests = Guest.objects.filter(room=room, is_active=True)
    if guests.exists():
        rooms_with_tenants.append(room)
    else:
        rooms_without_tenants.append(room)

print(f"  ✅ Rooms with tenants: {len(rooms_with_tenants)}")
print(f"  ❌ Rooms WITHOUT tenants: {len(rooms_without_tenants)}")

if rooms_without_tenants:
    print(f"\nRooms needing tenants:")
    for room in rooms_without_tenants:
        print(f"  • {room.number}")

print("\n" + "=" * 80)
print("CREATING TENANTS FOR EMPTY BOOKED ROOMS")
print("=" * 80)

created_count = 0

for room in rooms_without_tenants:
    try:
        # Generate random but realistic tenant info
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{created_count}@example.com"
        phone = f"98{random.randint(1000000000, 9999999999)}"
        gender = random.choice(['M', 'F'])
        city = random.choice(cities)
        state = random.choice(states)
        
        # Create guest
        guest = Guest.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            gender=gender,
            id_type='Aadhaar',
            id_number=f"{random.randint(100000000000, 999999999999)}",
            address=f"Address in {city}",
            city=city,
            state=state,
            country='India',
            zip_code=f"{random.randint(100000, 999999)}",
            room=room,
            is_active=True,
            check_in_date=datetime.now() - timedelta(days=random.randint(1, 30)),
            check_out_date=datetime.now() + timedelta(days=random.randint(10, 90)),
            lpu_id=f"LPU{random.randint(100000, 999999)}",
            notes=f"Tenant added on {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        # Add ID proof image
        img_io = create_test_image(f"id_proof_{room.number}")
        guest.id_proof_image.save(f'id_proof_{room.number}.jpg', img_io, save=False)
        guest.save()
        
        created_count += 1
        print(f"✓ {room.number}: Created {guest.full_name}")
        print(f"  ├─ Email: {email}")
        print(f"  ├─ Phone: {phone}")
        print(f"  ├─ ID: {guest.id_number}")
        print(f"  ├─ LPU ID: {guest.lpu_id}")
        print(f"  └─ Check-out: {guest.check_out_date.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"✗ {room.number}: Error - {str(e)}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

final_stats = {
    'booked_rooms': Room.objects.filter(is_available=False).count(),
    'rooms_with_tenants': Guest.objects.filter(is_active=True).values('room').distinct().count(),
    'total_guests': Guest.objects.filter(is_active=True).count(),
    'rooms_still_empty': 0
}

# Check if any booked rooms still empty
for room in Room.objects.filter(is_available=False):
    if not Guest.objects.filter(room=room, is_active=True).exists():
        final_stats['rooms_still_empty'] += 1

print(f"""
Total booked rooms: {final_stats['booked_rooms']}
Rooms with tenants: {final_stats['rooms_with_tenants']}
Total active guests: {final_stats['total_guests']}
Tenants created: {created_count}
Empty booked rooms: {final_stats['rooms_still_empty']} ❌

Status: {'✅ ALL BOOKED ROOMS POPULATED' if final_stats['rooms_still_empty'] == 0 else '⚠️  SOME ROOMS STILL EMPTY'}
""")

print("=" * 80)
