import sys, os, pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
while BASE_DIR.parent != BASE_DIR and not (BASE_DIR / 'manage.py').exists():
    BASE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
import django
django.setup()

from datetime import date
from django.test import Client
from django.contrib.auth.models import User
from rental.models import Guest, Room

def run_lifecycle_test():
    client = Client()
    
    print("="*60)
    print("      FULL TENANT LIFECYCLE VERIFICATION REPORT")
    print("="*60)
    
    # 1. Login
    print("[1] Logging in as Admin...")
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    admin_user.set_password('admin')
    admin_user.save()
    
    login_success = client.login(username='admin', password='admin')
    if not login_success:
        print("❌ FATAL: Login Failed.")
        return
    print("✅ Login Successful.")

    # 2. Baseline Stats
    print("\n[2] Establishing Baseline...")
    initial_active = Guest.objects.filter(is_active=True).count()
    print(f"   - Initial Active Guests: {initial_active}")
    
    # Find an available room
    test_room = Room.objects.filter(is_available=True).first()
    if not test_room:
        print("❌ FATAL: No available rooms for testing.")
        return
    initial_room_occupancy = test_room.current_occupancy
    print(f"   - Selected Room: {test_room.number} (Occupancy: {initial_room_occupancy}/{test_room.capacity})")

    # 3. Entry (Registration)
    print("\n[3] ACTION: Registering New Tenant 'LifeCycle TestUser'...")
    form_data = {
        'first_name': 'LifeCycle',
        'last_name': 'TestUser',
        'phone': '9998887777',
        'email': 'lifecycle@test.com',
        'room_id': test_room.id,
        'check_in_date': str(date.today()),
        'agreed_rent': '7000',
        'occupancy_preference': 'double',
        'occupation': 'student',
    }
    
    resp = client.post("/api/guest/add/", data=form_data)
    print(f"   - HTTP Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ Registration Failed: {resp.content.decode()}")
        return

    # 4. Verify Entry
    print("\n[4] VERIFICATION: Post-Entry State...")
    new_active = Guest.objects.filter(is_active=True).count()
    test_room.refresh_from_db()
    
    guest = Guest.objects.get(first_name='LifeCycle', last_name='TestUser')
    
    failures = []
    if new_active != initial_active + 1:
        failures.append(f"Guest Count did not increment correctly (Expected {initial_active + 1}, Got {new_active})")
    if test_room.current_occupancy != initial_room_occupancy + 1:
        failures.append(f"Room Occupancy did not increment (Expected {initial_room_occupancy + 1}, Got {test_room.current_occupancy})")
    if not guest.is_active:
         failures.append("Guest record is not marked ACTIVE")

    if failures:
        print("❌ INTEGRITY ERROR POST-ENTRY:")
        for f in failures: print(f"   - {f}")
        return
    else:
        print("✅ Data Integrity Confirmed: Guest Active, Room Occupancy Updated.")

    # 5. Dashboard Visual Check
    print("\n[5] VERIFICATION: Dashboard Visibility...")
    mg_resp = client.get("/manage-guests/")
    if "LifeCycle" in mg_resp.content.decode():
        print("✅ Guest appears on Manage Guests page.")
    else:
        print("❌ Guest NOT found on HTML page.")
    
    # 6. Checkout (End Tenancy)
    print("\n[6] ACTION: Ending Tenancy...")
    checkout_url = f"/api/guest/{guest.id}/checkout/"
    co_resp = client.post(checkout_url)
    
    print(f"   - HTTP Status: {co_resp.status_code}")

    # 7. Final Verification
    print("\n[7] VERIFICATION: Post-Checkout State...")
    final_active = Guest.objects.filter(is_active=True).count()
    test_room.refresh_from_db()
    guest.refresh_from_db()
    
    failures = []
    if final_active != initial_active:
        failures.append(f"Guest Count did not return to baseline (Expected {initial_active}, Got {final_active})")
    if test_room.current_occupancy != initial_room_occupancy:
         failures.append(f"Room Occupancy did not return to baseline (Expected {initial_room_occupancy}, Got {test_room.current_occupancy})")
    if guest.is_active:
        failures.append("Guest is still marked ACTIVE in DB")
    if not guest.check_out_date:
        failures.append("Check-out date was not set")

    if failures:
        print("❌ INTEGRITY ERROR POST-CHECKOUT:")
        for f in failures: print(f"   - {f}")
    else:
        print("✅ SYSTEM INTEGRITY CONFIRMED 100%")
        print("   - Guest moved to Archive.")
        print("   - Room slot freed.")
        print("   - Active counts balanced.")

    # Cleanup
    guest.delete()
    print("\nTest User Deleted from DB.")

if __name__ == "__main__":
    run_lifecycle_test()
