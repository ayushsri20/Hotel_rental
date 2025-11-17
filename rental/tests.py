from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Room, ElectricityBill, Guest
from django.core.files.uploadedfile import SimpleUploadedFile
import json


class ElectricityBillFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # create admin user
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        # create a sample room
        self.room = Room.objects.create(number='A-101', price=2000.0, is_available=True)

    def test_create_bill_with_month_yyyy_mm(self):
        self.client.login(username='admin', password='password')
        url = reverse('create_electricity_bill')
        data = {
            'room_id': str(self.room.id),
            'month': '2025-11',
            'starting_reading': '100.0',
            'ending_reading': '150.0',
            'rate_per_unit': '8.5',
            'due_date': '2025-11-20'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        # bill should be created
        bill = ElectricityBill.objects.filter(room=self.room).first()
        self.assertIsNotNone(bill)
        self.assertEqual(bill.units_consumed, 50.0)

    def test_create_bill_missing_month(self):
        self.client.login(username='admin', password='password')
        url = reverse('create_electricity_bill')
        data = {
            'room_id': str(self.room.id),
            'starting_reading': '100.0',
            'ending_reading': '150.0',
            'rate_per_unit': '8.5',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        resp = json.loads(response.content)
        self.assertFalse(resp.get('success'))

    def test_create_bill_ending_less_than_start(self):
        self.client.login(username='admin', password='password')
        url = reverse('create_electricity_bill')
        data = {
            'room_id': str(self.room.id),
            'month': '2025-11',
            'starting_reading': '200.0',
            'ending_reading': '150.0',
            'rate_per_unit': '8.5',
            'due_date': '2025-11-20'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        resp = json.loads(response.content)
        self.assertFalse(resp.get('success'))


class GuestFileUploadTests(TestCase):
    """Test file upload functionality for guest documents"""
    
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        self.room = Room.objects.create(number='B-201', price=3000.0, is_available=True)
    
    def test_add_guest_with_id_proof_image(self):
        """Test adding guest with ID proof image"""
        self.client.login(username='admin', password='password')
        
        # Create a small test image
        image_content = b'fake image content'
        test_image = SimpleUploadedFile(
            "id_proof.jpg",
            image_content,
            content_type="image/jpeg"
        )
        
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@test.com',
            'phone': '9876543210',
            'id_type': 'Aadhar',
            'id_number': '12345678',
            'check_in_date': '2025-11-01',
            'id_proof_image': test_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'), f"Error: {resp.get('message')}")
        
        # Verify guest was created with image
        guest = Guest.objects.get(email='john@test.com')
        self.assertTrue(guest.id_proof_image)
    
    def test_add_guest_with_lpu_id_photo(self):
        """Test adding guest with LPU ID photo"""
        self.client.login(username='admin', password='password')
        
        test_image = SimpleUploadedFile(
            "lpu_id.png",
            b'fake png content',
            content_type="image/png"
        )
        
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@test.com',
            'phone': '9876543211',
            'lpu_id': 'LP00123456',
            'check_in_date': '2025-11-01',
            'lpu_id_photo': test_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        
        guest = Guest.objects.get(email='jane@test.com')
        self.assertEqual(guest.lpu_id, 'LP00123456')
        self.assertTrue(guest.lpu_id_photo)
    
    def test_add_guest_with_document_verification(self):
        """Test adding guest with document verification image"""
        self.client.login(username='admin', password='password')
        
        test_image = SimpleUploadedFile(
            "doc_verify.jpg",
            b'fake verification image',
            content_type="image/jpeg"
        )
        
        data = {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'email': 'bob@test.com',
            'phone': '9876543212',
            'check_in_date': '2025-11-01',
            'document_verification_image': test_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        
        guest = Guest.objects.get(email='bob@test.com')
        self.assertTrue(guest.document_verification_image)
    
    def test_guest_with_all_document_images(self):
        """Test guest with all three document images"""
        self.client.login(username='admin', password='password')
        
        id_image = SimpleUploadedFile("id.jpg", b'id image', content_type="image/jpeg")
        lpu_image = SimpleUploadedFile("lpu.png", b'lpu image', content_type="image/png")
        doc_image = SimpleUploadedFile("doc.jpg", b'doc image', content_type="image/jpeg")
        
        data = {
            'first_name': 'Alice',
            'last_name': 'Cooper',
            'email': 'alice@test.com',
            'phone': '9876543213',
            'id_type': 'Passport',
            'id_number': 'PASS123456',
            'lpu_id': 'LP00654321',
            'check_in_date': '2025-11-01',
            'id_proof_image': id_image,
            'lpu_id_photo': lpu_image,
            'document_verification_image': doc_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'), f"Error: {resp.get('message')}")
        
        guest = Guest.objects.get(email='alice@test.com')
        self.assertTrue(guest.id_proof_image)
        self.assertTrue(guest.lpu_id_photo)
        self.assertTrue(guest.document_verification_image)
    
    def test_add_guest_with_invalid_file_extension(self):
        """Test that invalid file types are rejected"""
        self.client.login(username='admin', password='password')
        
        # Try to upload a text file instead of image
        bad_file = SimpleUploadedFile(
            "not_image.txt",
            b'This is not an image',
            content_type="text/plain"
        )
        
        data = {
            'first_name': 'BadFile',
            'last_name': 'User',
            'email': 'badfile@test.com',
            'phone': '9876543214',
            'check_in_date': '2025-11-01',
            'id_proof_image': bad_file,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 400)
        resp = json.loads(response.content)
        self.assertFalse(resp.get('success'))
        self.assertIn('image type', resp.get('message', '').lower())
    
    def test_update_guest_with_new_image(self):
        """Test updating guest with new image"""
        self.client.login(username='admin', password='password')
        
        # Create initial guest
        guest = Guest.objects.create(
            first_name='Update',
            last_name='Test',
            email='update@test.com',
            phone='9876543215'
        )
        
        # Update with new image
        new_image = SimpleUploadedFile(
            "updated_id.jpg",
            b'updated image content',
            content_type="image/jpeg"
        )
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Guest',
            'phone': '9876543215',
            'id_proof_image': new_image,
        }
        
        response = self.client.post(reverse('update_guest', args=[guest.id]), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        
        # Verify update
        guest.refresh_from_db()
        self.assertEqual(guest.first_name, 'Updated')
        self.assertTrue(guest.id_proof_image)
