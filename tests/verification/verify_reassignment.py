import sys, os, pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / 'manage.py').exists():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
import django
django.setup()

from datetime import date, timedelta
from django.test import Client
from django.contrib.auth.models import User
from rental.models import Guest, Room

def run_reassignment_test():
    client = Client()
    
    print("="*60)
    print("      ROOM REASSIGNMENT & LONG-TERM TEST")
    print("="*60)
    
    # 1. Login
    print("[1] Logging in as Admin...")
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    admin_user.set_password('admin')
    admin_user.save()
    
    client.login(username='admin', password='admin')

    # 2. Select Test Room
    all_rooms = Room.objects.filter(is_available=True)
    test_room = None
    for r in all_rooms:
        if r.current_occupancy == 0:
            test_room = r
            break
            
    if not test_room: 
        print("❌ FATAL: No empty rooms available.")
        return
    print(f"✅ Selected Test Room: {test_room.number} (Empty)")

    # 3. Tenant A: "Old Resident" (Check-in 2 months ago)
    check_in_date = date.today() - timedelta(days=60)
    print(f"\n[2] Registering Tenant A (Old Resident)...")
    print(f"    - Check-in Date: {check_in_date}")
    
    data_a = {
        'first_name': 'Tenant', 'last_name': 'Alpha',
        'phone': '1111111111', 'email': 'alpha@test.com',
        'room_id': test_room.id,
        'check_in_date': str(check_in_date),
        'agreed_rent': '7000', 'occupancy_preference': 'double', 'occupation': 'student',
    }
    resp = client.post("/api/guest/add/", data=data_a)
    
    if resp.status_code != 200:
        print(f"❌ Tenant A Registration Failed: {resp.content.decode()}")
        return
        
    guest_a = Guest.objects.get(first_name='Tenant', last_name='Alpha')
    test_room.refresh_from_db()
    print(f"✅ Tenant A Registered (ID: {guest_a.id}). Room Occupancy: {test_room.current_occupancy}")

    # 4. Checkout Tenant A (Today)
    print(f"\n[3] Checking out Tenant A...")
    checkout_url = f"/api/guest/{guest_a.id}/checkout/"
    client.post(checkout_url)
    
    guest_a.refresh_from_db()
    test_room.refresh_from_db()
    
    if not guest_a.is_active and guest_a.check_out_date == date.today():
        print(f"✅ Tenant A Archived. Check-out Date: {guest_a.check_out_date}")
        print(f"✅ Room {test_room.number} Status: Available (Occupancy: {test_room.current_occupancy})")
    else:
        print("❌ Checkout Failed.")
        return

    # 5. Tenant B: "New Resident" (Check-in Today)
    print(f"\n[4] Registering Tenant B (New Resident) into SAME Room {test_room.number}...")
    data_b = {
        'first_name': 'Tenant', 'last_name': 'Beta',
        'phone': '2222222222', 'email': 'beta@test.com',
        'room_id': test_room.id, # SAME ROOM ID
        'check_in_date': str(date.today()),
        'agreed_rent': '7500',
        'occupancy_preference': 'double', 'occupation': 'professional',
    }
    
    resp_b = client.post("/api/guest/add/", data=data_b)
    
    if resp_b.status_code != 200:
        print(f"❌ Tenant B Reassignment Failed: {resp_b.content.decode()}")
        return

    guest_b = Guest.objects.get(first_name='Tenant', last_name='Beta')
    test_room.refresh_from_db()
    
    if guest_b.room == test_room and guest_b.is_active:
        print(f"✅ REASSIGNMENT SUCCESSFUL!")
        print(f"   - Room {test_room.number} is now occupied by Tenant B (ID: {guest_b.id}).")
        print(f"   - Current Occupancy: {test_room.current_occupancy}")
        print(f"   - Tenant A is still Archived (History preserved).")
    else:
        print("❌ Reassignment Logic Failed.")

    # Cleanup
    guest_a.delete()
    guest_b.delete()
    print("\nTest Data Cleaned up.")

if __name__ == "__main__":
    run_reassignment_test()
