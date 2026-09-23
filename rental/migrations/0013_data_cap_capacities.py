"""
Data migration to cap all room capacities at 2 tenants and report any issues.
"""
from django.db import migrations
import logging

logger = logging.getLogger(__name__)

def cap_room_capacities(apps, schema_editor):
    """Cap all room capacities at 2 and report any rooms with >2 active tenants"""
    Room = apps.get_model('rental', 'Room')
    Guest = apps.get_model('rental', 'Guest')
    
    updated_count = 0
    problem_rooms = []
    
    # Update all rooms with capacity > 2
    for room in Room.objects.filter(capacity__gt=2):
        old_capacity = room.capacity
        room.capacity = 2
        room.save()
        updated_count += 1
        
        # Check if this room has more than 2 active tenants
        active_tenants = Guest.objects.filter(room=room, is_active=True).count()
        if active_tenants > 2:
            problem_rooms.append({
                'room_number': room.number,
                'old_capacity': old_capacity,
                'active_tenants': active_tenants
            })
    
    if problem_rooms:
        logger.warning(
            "Capacity migration found %s rooms with more than 2 active tenants: %s",
            len(problem_rooms),
            problem_rooms,
        )
    else:
        logger.info("Capacity migration capped %s rooms at 2 tenants", updated_count)

def reverse_cap(apps, schema_editor):
    """Reverse migration - restore original capacities (not recommended)"""
    logger.warning("Reverse migration cannot restore original room capacities")

class Migration(migrations.Migration):

    dependencies = [
        ('rental', '0012_cap_room_capacity_at_2'),
    ]


    operations = [
        migrations.RunPython(cap_room_capacities, reverse_cap),
    ]
