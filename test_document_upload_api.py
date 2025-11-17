#!/usr/bin/env python3
"""
Test script to verify document upload API endpoints and building tenant details modal
"""
import os
import sys
import django
from io import BytesIO
from PIL import Image

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_project.settings')
sys.path.insert(0, '/Users/ayush/hotel_rental/hotel_project')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from rental.models import Room, Guest
from datetime import datetime, timedelta

def create_test_image(filename='test.jpg'):
    """Create a test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    img_io.name = filename
    return img_io

def test_document_upload_workflow():
    """Test complete document upload workflow"""
    print("\n" + "="*80)
    print("TESTING DOCUMENT UPLOAD WORKFLOW")
    print("="*80)
    
    # Create test user and login
    user, created = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'email': 'admin@test.com'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✓ Created test admin user: {user.username}")
    else:
        print(f"✓ Using existing test admin user: {user.username}")
    
    client = Client()
    login_result = client.login(username='admin_test', password='testpass123')
    print(f"✓ Admin login: {'SUCCESS' if login_result else 'FAILED'}")
    
    # Create test room
    room, _ = Room.objects.get_or_create(
        number='B-101',
        defaults={
            'room_type': 'double',
            'is_available': False,
            'price': 5000
        }
    )
    print(f"✓ Test room created/found: {room.number}")
    
    # Create test guest
    guest, created = Guest.objects.get_or_create(
        email='tenant@test.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'Tenant',
            'phone': '9999999999',
            'gender': 'M',
            'id_type': 'Aadhaar',
            'id_number': '123456789012',
            'address': 'Test Address',
            'city': 'Test City',
            'state': 'Test State',
            'country': 'India',
            'zip_code': '123456',
            'room': room,
            'is_active': True,
            'check_in_date': datetime.now(),
            'check_out_date': datetime.now() + timedelta(days=30)
        }
    )
    print(f"✓ Test guest created: {guest.full_name} (ID: {guest.id})")
    
    # Test 1: Get room tenants API
    print("\n--- Test 1: Get Room Tenants API ---")
    response = client.get(f'/api/room/{room.id}/tenants/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Room: {data.get('room')}")
        print(f"Tenants Count: {len(data.get('tenants', []))}")
        
        if data.get('tenants'):
            tenant = data['tenants'][0]
            print(f"Tenant Name: {tenant.get('name')}")
            print(f"Tenant ID: {tenant.get('id')}")
            print(f"Has ID Proof Image: {bool(tenant.get('id_proof_image'))}")
            print(f"Has LPU ID Photo: {bool(tenant.get('lpu_id_photo'))}")
            print(f"Has Verification Image: {bool(tenant.get('document_verification_image'))}")
            print("✓ API Response Structure Valid")
        else:
            print("⚠ No tenants returned (will be populated after upload)")
    else:
        print(f"✗ Error: {response.content.decode()}")
    
    # Test 2: Upload ID Proof Image
    print("\n--- Test 2: Upload ID Proof Image ---")
    image_file = create_test_image('id_proof.jpg')
    response = client.post(f'/api/guest/{guest.id}/update/', {
        'id_proof_image': image_file
    })
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message', data.get('error', 'No message'))}")
        
        # Refresh guest from DB
        guest.refresh_from_db()
        print(f"ID Proof Image saved: {bool(guest.id_proof_image)}")
        if guest.id_proof_image:
            print(f"Image path: {guest.id_proof_image.url}")
        print("✓ ID Proof Upload Successful")
    else:
        print(f"✗ Error: {response.json()}")
    
    # Test 3: Upload LPU ID with Photo
    print("\n--- Test 3: Upload LPU ID with Photo ---")
    image_file = create_test_image('lpu_id.jpg')
    response = client.post(f'/api/guest/{guest.id}/update/', {
        'lpu_id': 'LPU123456',
        'lpu_id_photo': image_file
    })
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        
        guest.refresh_from_db()
        print(f"LPU ID: {guest.lpu_id}")
        print(f"LPU Photo saved: {bool(guest.lpu_id_photo)}")
        if guest.lpu_id_photo:
            print(f"Image path: {guest.lpu_id_photo.url}")
        print("✓ LPU ID Upload Successful")
    else:
        print(f"✗ Error: {response.json()}")
    
    # Test 4: Upload Verification Document
    print("\n--- Test 4: Upload Verification Document ---")
    image_file = create_test_image('verification.jpg')
    response = client.post(f'/api/guest/{guest.id}/update/', {
        'document_verification_image': image_file
    })
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        
        guest.refresh_from_db()
        print(f"Verification Image saved: {bool(guest.document_verification_image)}")
        if guest.document_verification_image:
            print(f"Image path: {guest.document_verification_image.url}")
        print("✓ Verification Document Upload Successful")
    else:
        print(f"✗ Error: {response.json()}")
    
    # Test 5: Verify GET room tenants now returns document URLs
    print("\n--- Test 5: Verify Tenant Details Include Document URLs ---")
    response = client.get(f'/api/room/{room.id}/tenants/')
    
    if response.status_code == 200:
        data = response.json()
        if data.get('tenants'):
            tenant = data['tenants'][0]
            print(f"Tenant: {tenant.get('name')}")
            print(f"Has ID Proof URL: {bool(tenant.get('id_proof_image'))}")
            print(f"Has LPU Photo URL: {bool(tenant.get('lpu_id_photo'))}")
            print(f"Has Verification URL: {bool(tenant.get('document_verification_image'))}")
            print(f"LPU ID Field: {tenant.get('lpu_id')}")
            
            if all([
                tenant.get('id_proof_image'),
                tenant.get('lpu_id_photo'),
                tenant.get('document_verification_image'),
                tenant.get('lpu_id')
            ]):
                print("✓ ALL DOCUMENT FIELDS PRESENT IN API RESPONSE")
            else:
                print("⚠ Some document fields missing")
    else:
        print(f"✗ Error: {response.status_code}")
    
    # Test 6: Test invalid file upload
    print("\n--- Test 6: Test Invalid File Rejection ---")
    # Create a text file
    invalid_file = BytesIO(b"This is not an image")
    invalid_file.name = "test.txt"
    
    response = client.post(f'/api/guest/{guest.id}/update/', {
        'id_proof_image': invalid_file
    })
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 400:
        print(f"✓ Invalid file correctly rejected: {response.json().get('message', 'Bad file')}")
    else:
        print(f"⚠ Unexpected status code for invalid file: {response.status_code}")
    
    print("\n" + "="*80)
    print("DOCUMENT UPLOAD WORKFLOW TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    test_document_upload_workflow()
