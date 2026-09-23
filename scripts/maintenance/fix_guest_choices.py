import os
import django

import sys, os, pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / 'manage.py').exists():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
import django
django.setup()

from rental.models import Guest

def fix_guest_choices():
    guests = Guest.objects.all()
    count = 0
    for guest in guests:
        updated = False
        if guest.occupancy_preference and guest.occupancy_preference[0].isupper():
            print(f"Fixing Guest {guest.id}: {guest.occupancy_preference} -> {guest.occupancy_preference.lower()}")
            guest.occupancy_preference = guest.occupancy_preference.lower()
            updated = True
            
        if guest.gender and len(guest.gender) > 1:
             # Just in case 'Male' instead of 'M'
             if guest.gender == 'Male': guest.gender = 'M'
             if guest.gender == 'Female': guest.gender = 'F'
             updated = True

        if updated:
            guest.save()
            count += 1
            
    print(f"Fixed {count} guests.")

if __name__ == '__main__':
    fix_guest_choices()
