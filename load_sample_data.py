#!/usr/bin/env python3
"""
Sample data loader for Panesar PG Hotel Management System
Run this to populate the database with sample rooms
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import Room

def create_sample_rooms():
    """Create sample rooms for all buildings if they don't exist"""
    
    # M1 Complex (A)
    m1_rooms = [
        ('A-101', 'single', 8000),
        ('A-102', 'single', 8000),
        ('A-103', 'double', 12000),
        ('A-104', 'double', 12000),
        ('A-201', 'single', 8500),
        ('A-202', 'suite', 15000),
    ]
    
    # Building 1 (B)
    building1_rooms = [
        ('B-101', 'single', 7500),
        ('B-102', 'single', 7500),
        ('B-103', 'double', 11000),
        ('B-201', 'double', 11500),
    ]
    
    # Building 2 (C)
    building2_rooms = [
        ('C-101', 'single', 7000),
        ('C-102', 'single', 7000),
        ('C-103', 'double', 10500),
        ('C-201', 'suite', 14000),
    ]
    
    # Building 3 (D)
    building3_rooms = [
        ('D-101', 'single', 7500),
        ('D-102', 'double', 11000),
        ('D-201', 'double', 11500),
    ]
    
    # Building 4 (E)
    building4_rooms = [
        ('E-101', 'single', 7000),
        ('E-102', 'single', 7000),
        ('E-103', 'double', 10500),
    ]
    
    all_rooms = m1_rooms + building1_rooms + building2_rooms + building3_rooms + building4_rooms
    
    created_count = 0
    skipped_count = 0
    
    for room_number, room_type, price in all_rooms:
        if not Room.objects.filter(number=room_number).exists():
            Room.objects.create(
                number=room_number,
                room_type=room_type,
                price=price,
                is_available=True
            )
            created_count += 1
            print(f"✓ Created room {room_number}")
        else:
            skipped_count += 1
            print(f"- Skipped {room_number} (already exists)")
    
    print(f"\n{'='*50}")
    print(f"Created: {created_count} rooms")
    print(f"Skipped: {skipped_count} rooms (already exist)")
    print(f"Total: {Room.objects.count()} rooms in database")
    print(f"{'='*50}")

if __name__ == '__main__':
    create_sample_rooms()
