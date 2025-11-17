#!/usr/bin/env python3
"""
Fix room availability status based on actual guest occupancy
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
sys.path.insert(0, '/Users/ayush/hotel_rental/hotel_project')
django.setup()

from rental.models import Room, Guest

print("=" * 80)
print("FIXING ROOM AVAILABILITY STATUS")
print("=" * 80)

total_rooms = Room.objects.count()
updated_count = 0

for room in Room.objects.all():
    # Check if room has active guests
    has_guests = Guest.objects.filter(room=room, is_active=True).exists()
    
    # If room has guests but is marked available, mark as booked
    if has_guests and room.is_available:
        room.is_available = False
        room.save()
        updated_count += 1
        print(f"✓ {room.number}: Marked BOOKED (has {Guest.objects.filter(room=room, is_active=True).count()} guests)")
    
    # If room has no guests but is marked booked, mark as available
    elif not has_guests and not room.is_available:
        room.is_available = True
        room.save()
        updated_count += 1
        print(f"✓ {room.number}: Marked AVAILABLE (no guests)")
    
    else:
        # Status is correct, no change needed
        status = "BOOKED" if has_guests else "AVAILABLE"
        print(f"  {room.number}: {status} (correct)")

print("\n" + "=" * 80)
print(f"SUMMARY")
print("=" * 80)
print(f"Total Rooms: {total_rooms}")
print(f"Rooms Updated: {updated_count}")
print(f"Available Rooms: {Room.objects.filter(is_available=True).count()}")
print(f"Booked Rooms: {Room.objects.filter(is_available=False).count()}")
print("=" * 80)
