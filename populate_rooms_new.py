#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import Room

# Clear existing rooms
Room.objects.all().delete()

# Create 6 buildings (A-F) with 6 rooms each
# 3 rooms @ $6000 and 3 rooms @ $8500 per building
buildings = ['A', 'B', 'C', 'D', 'E', 'F']

for building in buildings:
    # First 3 rooms at $6000
    for room_num in range(1, 4):
        room_number = f"{building}-{room_num:02d}"
        room = Room.objects.create(
            number=room_number,
            room_type='double',
            price=6000,
            is_available=True
        )
        print(f"✓ Created room {room_number} - ₹6000")
    
    # Next 3 rooms at $8500
    for room_num in range(4, 7):
        room_number = f"{building}-{room_num:02d}"
        room = Room.objects.create(
            number=room_number,
            room_type='double',
            price=8500,
            is_available=True
        )
        print(f"✓ Created room {room_number} - ₹8500")

total = Room.objects.count()
print(f"\n✅ Total rooms created: {total}")
print(f"✅ Distribution: 3 rooms @ ₹6000 and 3 rooms @ ₹8500 per building")
print(f"✅ Expected: 6 buildings × 6 rooms = {6*6} rooms")
