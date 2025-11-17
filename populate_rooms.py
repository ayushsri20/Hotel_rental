#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import Room

# Clear existing rooms
Room.objects.all().delete()

# Create 6 buildings (A-F) with 6 rooms each
buildings = ['A', 'B', 'C', 'D', 'E', 'F']
room_types = ['single', 'double', 'suite']
prices = {'single': 50, 'double': 75, 'suite': 150}

count = 0
for building in buildings:
    for room_num in range(1, 7):
        room_number = f"{building}-{room_num:02d}"
        room_type = room_types[room_num % 3]
        
        room = Room.objects.create(
            number=room_number,
            room_type=room_type,
            price=prices[room_type],
            is_available=True
        )
        count += 1
        print(f"✓ Created room {room_number} ({room_type})")

print(f"\n✅ Total rooms created: {count}")
