#!/usr/bin/env python3
"""
Direct production data loader - creates all 36 rooms
Run this on Railway to populate the database
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
django.setup()

from rental.models import Room

def load_all_rooms():
    """Create all 36 rooms across 6 buildings"""
    
    rooms_data = [
        # M1 Complex (A) - 6 rooms
        ('A-101', 'single', 7500),
        ('A-102', 'single', 7500),
        ('A-103', 'double', 8000),
        ('A-104', 'double', 8000),
        ('A-105', 'suite', 7000),
        ('A-106', 'single', 7000),
        
        # Building 1 (B) - 6 rooms
        ('B-101', 'single', 7000),
        ('B-102', 'single', 7000),
        ('B-103', 'double', 7000),
        ('B-104', 'double', 7000),
        ('B-105', 'single', 7000),
        ('B-106', 'single', 7000),
        
        # Building 2 (C) - 6 rooms
        ('C-101', 'single', 7000),
        ('C-102', 'single', 7000),
        ('C-103', 'double', 7000),
        ('C-104', 'double', 7000),
        ('C-105', 'single', 7000),
        ('C-106', 'suite', 7000),
        
        # Building 3 (D) - 6 rooms
        ('D-101', 'single', 7000),
        ('D-102', 'single', 7000),
        ('D-103', 'double', 7000),
        ('D-104', 'double', 7000),
        ('D-105', 'single', 7000),
        ('D-106', 'single', 7000),
        
        # Building 4 (E) - 6 rooms
        ('E-101', 'single', 7000),
        ('E-102', 'single', 7000),
        ('E-103', 'double', 7000),
        ('E-104', 'double', 7000),
        ('E-105', 'single', 7000),
        ('E-106', 'single', 7000),
        
        # Building 5 (F) - 6 rooms
        ('F-101', 'single', 7000),
        ('F-102', 'single', 7000),
        ('F-103', 'double', 7000),
        ('F-104', 'double', 7000),
        ('F-105', 'single', 7000),
        ('F-106', 'single', 7000),
    ]
    
    created = 0
    skipped = 0
    
    print("\n" + "="*60)
    print("Loading 36 Rooms into Production Database")
    print("="*60 + "\n")
    
    for room_number, room_type, price in rooms_data:
        if not Room.objects.filter(number=room_number).exists():
            Room.objects.create(
                number=room_number,
                room_type=room_type,
                price=price,
                is_available=True
            )
            created += 1
            print(f"✓ Created {room_number}")
        else:
            skipped += 1
            print(f"- Skipped {room_number} (exists)")
    
    print("\n" + "="*60)
    print(f"Created: {created} | Skipped: {skipped}")
    print(f"Total rooms in database: {Room.objects.count()}")
    print("="*60 + "\n")

if __name__ == '__main__':
    load_all_rooms()
