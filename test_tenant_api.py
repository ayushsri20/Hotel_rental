#!/usr/bin/env python3
"""
Test the tenant details API from building tiles
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
sys.path.insert(0, '/Users/ayush/hotel_rental/hotel_project')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from rental.models import Room
import json

print("=" * 80)
print("TESTING TENANT DETAILS API")
print("=" * 80)

# Create admin user
admin, created = User.objects.get_or_create(
    username='admin_test',
    defaults={
        'is_staff': True,
        'is_superuser': True,
        'email': 'admin@test.com'
    }
)

if created:
    admin.set_password('testpass123')
    admin.save()
    print(f"✓ Created admin user")
else:
    print(f"✓ Using existing admin user")

# Login
client = Client()
login_result = client.login(username='admin_test', password='testpass123')
print(f"✓ Admin login: {'SUCCESS' if login_result else 'FAILED'}")

# Test API for each booked room
print("\n" + "=" * 80)
print("TESTING ROOMS")
print("=" * 80)

for room in Room.objects.filter(is_available=False):
    response = client.get(f'/api/room/{room.id}/tenants/')
    print(f"\n--- Room {room.number} (ID: {room.id}) ---")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Room: {data.get('room')}")
        print(f"Tenants Count: {len(data.get('tenants', []))}")
        
        for tenant in data.get('tenants', []):
            print(f"\n  Tenant: {tenant.get('name')}")
            print(f"  ID: {tenant.get('id')}")
            print(f"  Email: {tenant.get('email')}")
            print(f"  Phone: {tenant.get('phone')}")
            print(f"  Check-in: {tenant.get('check_in')}")
            print(f"  Check-out: {tenant.get('check_out')}")
            print(f"  LPU ID: {tenant.get('lpu_id', 'N/A')}")
            print(f"  Has ID Proof: {bool(tenant.get('id_proof_image'))}")
            print(f"  Has LPU Photo: {bool(tenant.get('lpu_id_photo'))}")
            print(f"  Has Verification: {bool(tenant.get('document_verification_image'))}")
            
            if tenant.get('id_proof_image'):
                print(f"  ID Proof URL: {tenant.get('id_proof_image')}")
    else:
        print(f"Error: {response.content.decode()[:200]}")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
