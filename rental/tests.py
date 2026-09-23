from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from .models import Building, Room, ElectricityBill, Guest, MonthlyPayment, PaymentRecord, MaintenanceExpense
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from datetime import date
import json


@override_settings(
    MIDDLEWARE=[m for m in settings.MIDDLEWARE if 'LoginRequiredMiddleware' not in m],
    APPEND_SLASH=False
)
class ElectricityBillFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        # create admin user
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        # create a sample room
        self.room = Room.objects.create(number='A-101', room_type='single', price=2000.0, is_available=True)
        # Login the client
        self.client.force_login(self.admin)

    def test_create_bill_with_month_yyyy_mm(self):
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


@override_settings(
    MIDDLEWARE=[m for m in settings.MIDDLEWARE if 'LoginRequiredMiddleware' not in m],
    APPEND_SLASH=False
)
class GuestFileUploadTests(TestCase):
    """Test file upload functionality for guest documents"""
    
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='password')
        self.room = Room.objects.create(number='B-201', room_type='double', price=3000.0, is_available=True)
        self.client.force_login(self.admin)
    
    def test_add_guest_with_govt_id_photo(self):
        """Test adding guest with ID proof image"""
        
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
            'govt_id_photo': test_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'), f"Error: {resp.get('message')}")
        
        # Verify guest was created with image
        guest = Guest.objects.get(email='john@test.com')
        self.assertTrue(guest.govt_id_photo)
    
    def test_add_guest_with_college_id_photo(self):
        """Test adding guest with LPU ID photo"""
        
        test_image = SimpleUploadedFile(
            "college_id.png",
            b'fake png content',
            content_type="image/png"
        )
        
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane@test.com',
            'phone': '9876543211',
            'college_id': 'LP00123456',
            'check_in_date': '2025-11-01',
            'college_id_photo': test_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        
        guest = Guest.objects.get(email='jane@test.com')
        self.assertEqual(guest.college_id, 'LP00123456')
        self.assertTrue(guest.college_id_photo)
    
    def test_add_guest_with_document_verification(self):
        """Test adding guest with document verification image"""
        
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
            'college_id': 'LP00654321',
            'check_in_date': '2025-11-01',
            'govt_id_photo': id_image,
            'college_id_photo': lpu_image,
            'document_verification_image': doc_image,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'), f"Error: {resp.get('message')}")
        
        guest = Guest.objects.get(email='alice@test.com')
        self.assertTrue(guest.govt_id_photo)
        self.assertTrue(guest.college_id_photo)
        self.assertTrue(guest.document_verification_image)
    
    def test_add_guest_with_invalid_file_extension(self):
        """Test that invalid file types are rejected"""
        
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
            'govt_id_photo': bad_file,
        }
        
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 400)
        resp = json.loads(response.content)
        self.assertFalse(resp.get('success'))
        self.assertIn('image type', resp.get('message', '').lower())
    
    def test_update_guest_with_new_image(self):
        """Test updating guest with new image"""
        
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
            'govt_id_photo': new_image,
        }
        
        response = self.client.post(reverse('update_guest', args=[guest.id]), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'))
        
        # Verify update
        guest.refresh_from_db()
        self.assertEqual(guest.first_name, 'Updated')
        self.assertTrue(guest.govt_id_photo)


@override_settings(
    MIDDLEWARE=[m for m in settings.MIDDLEWARE if 'LoginRequiredMiddleware' not in m],
    APPEND_SLASH=False
)
class GuestCheckInPaymentTests(TestCase):
    """Auto-generated rent must use negotiated agreed_rent, not list price."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='password'
        )
        self.room = Room.objects.create(
            number='C-301',
            room_type='double',
            price=2000.0,
            is_available=True,
        )
        self.client.force_login(self.admin)

    def test_add_guest_monthly_payment_uses_agreed_rent(self):
        data = {
            'first_name': 'Priya',
            'last_name': 'Shah',
            'email': 'priya@test.com',
            'phone': '9876543299',
            'room_id': str(self.room.id),
            'check_in_date': date.today().isoformat(),
            'agreed_rent': '7000',
        }
        response = self.client.post(reverse('add_guest'), data)
        self.assertEqual(response.status_code, 200)
        resp = json.loads(response.content)
        self.assertTrue(resp.get('success'), f"Error: {resp.get('message')}")

        payment = MonthlyPayment.objects.filter(room=self.room).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.rent_amount, Decimal('7000.00'))
        self.room.refresh_from_db()
        self.assertEqual(self.room.agreed_rent, Decimal('7000.00'))

    def test_guest_save_uses_existing_agreed_rent(self):
        self.room.agreed_rent = Decimal('6500.00')
        self.room.save()
        guest = Guest.objects.create(
            first_name='Amit',
            last_name='Kumar',
            room=self.room,
            is_active=True,
            check_in_date=date.today(),
        )
        payment = MonthlyPayment.objects.get(room=self.room, guest=guest)
        self.assertEqual(payment.rent_amount, Decimal('6500.00'))

    def test_room_effective_rent_is_used_when_guest_rent_is_omitted(self):
        self.room.price = Decimal('8000.00')
        self.room.agreed_rent = Decimal('7001.00')
        self.room.save()
        response = self.client.post(reverse('add_guest'), {
            'first_name': 'Real',
            'last_name': 'Tenant',
            'room_id': str(self.room.id),
            'check_in_date': date.today().isoformat(),
            'agreed_rent': '',
        })
        self.assertEqual(response.status_code, 200)
        payment = MonthlyPayment.objects.get(room=self.room)
        self.assertEqual(payment.rent_amount, Decimal('7001.00'))
        self.room.refresh_from_db()
        self.assertEqual(self.room.effective_rent, Decimal('7001.00'))


@override_settings(
    MIDDLEWARE=[m for m in settings.MIDDLEWARE if 'LoginRequiredMiddleware' not in m],
    APPEND_SLASH=False
)
class BuildingRoomIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='building-admin', email='building@example.com', password='password'
        )
        self.client.force_login(self.admin)
        self.building = Building.objects.create(code='G', name='Building 6')

    def test_add_room_requires_and_persists_building(self):
        response = self.client.post(reverse('add_room'), {
            'room_number': 'G-101',
            'building_id': self.building.id,
            'room_type': 'double',
            'price': '8000',
            'capacity': '2',
        })
        self.assertEqual(response.status_code, 200)
        room = Room.objects.get(number='G-101')
        self.assertEqual(room.building, self.building)

    def test_room_rent_update_only_changes_unpaid_current_month(self):
        room = Room.objects.create(
            number='G-102', building=self.building, room_type='single', price=5000
        )
        month = date.today().replace(day=1)
        unpaid = MonthlyPayment.objects.create(room=room, month=month, rent_amount=5000)
        paid = MonthlyPayment.objects.create(
            room=room, month=date(2020, 1, 1), rent_amount=5000,
            paid_amount=Decimal('1000'), payment_status='partial'
        )
        response = self.client.post(reverse('update_room', args=[room.id]), {
            'number': room.number,
            'room_type': room.room_type,
            'capacity': room.capacity,
            'price': '6000',
            'agreed_rent': '6500',
            'building_id': self.building.id,
            'is_available': 'true',
        })
        self.assertEqual(response.status_code, 200)
        unpaid.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(unpaid.rent_amount, Decimal('6500.00'))
        self.assertEqual(paid.rent_amount, Decimal('5000.00'))

    def test_management_pages_render_for_admin(self):
        for route_name in ('manage_buildings', 'manage_guests', 'manage_payments', 'manage_electricity_bills'):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)

    def test_tenancy_form_exposes_building_and_room_data(self):
        room = Room.objects.create(
            number='G-105', building=self.building, room_type='double',
            price=8000, agreed_rent=7001,
        )
        response = self.client.get(reverse('manage_guests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="formBuilding"')
        self.assertContains(response, 'Building 6 (G)')
        self.assertContains(response, room.number)
        self.assertContains(response, 'effective_rent')

    def test_room_rent_flows_into_monthly_payment_form(self):
        room = Room.objects.create(
            number='G-103', building=self.building, room_type='double',
            price=8000, agreed_rent=7001,
        )
        response = self.client.post(reverse('create_monthly_payment'), {
            'room_id': room.id,
            'month': date.today().strftime('%Y-%m'),
        })
        self.assertEqual(response.status_code, 200)
        payment = MonthlyPayment.objects.get(room=room)
        self.assertEqual(payment.rent_amount, Decimal('7001.00'))

    def test_assignment_form_lists_all_rooms_and_rejects_closed_room(self):
        closed_room = Room.objects.create(
            number='G-104', building=self.building, room_type='double',
            price=7000, is_available=False,
        )
        response = self.client.get(reverse('manage_guests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is_available')

        response = self.client.post(reverse('add_guest'), {
            'first_name': 'Closed',
            'last_name': 'Room',
            'room_id': closed_room.id,
            'check_in_date': date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('closed', response.json()['message'].lower())

    def test_vacant_rooms_are_excluded_from_analytics_and_expenses_are_included(self):
        occupied = Room.objects.create(
            number='G-106', building=self.building, room_type='single', price=6000,
        )
        Room.objects.create(
            number='G-107', building=self.building, room_type='single', price=9000,
        )
        Guest.objects.create(
            first_name='Occupied', last_name='Tenant', room=occupied,
            check_in_date=date.today(), is_active=True,
        )
        MaintenanceExpense.objects.create(
            building_name='G', category='repairs', amount=Decimal('1000'),
            date=date.today(), description='Repair', is_paid=True,
        )
        MaintenanceExpense.objects.create(
            building_name='G', category='repairs', amount=Decimal('5000'),
            date=date(2020, 1, 15), description='Historical repair', is_paid=True,
        )
        response = self.client.get(reverse('performance_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_expected_rent'], 6000.0)
        self.assertEqual(response.context['total_maintenance_expenses'], 1000.0)
        self.assertEqual(response.context['net_revenue'], -1000.0)
        self.assertTrue(any(row['category'] == 'General Repairs' for row in response.context['expense_rows']))

        metrics = self.client.get(reverse('dashboard_metrics_api')).json()['metrics']
        self.assertEqual(metrics['resident_distribution']['G'], 1)

        response = self.client.post(reverse('record_maintenance'), {
            'building_name': 'G', 'category': 'cleaning', 'amount': '250',
            'date': date.today().isoformat(), 'description': 'Cleaning',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_ledger_rejects_overpayment(self):
        room = Room.objects.create(
            number='G-108', building=self.building, room_type='single', price=6000,
        )
        payment = MonthlyPayment.objects.create(
            room=room, month=date.today().replace(day=1), rent_amount=Decimal('6000.00')
        )
        response = self.client.post(reverse('record_payment'), {
            'payment_id': payment.id,
            'payment_amount': '6001',
            'payment_date': date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PaymentRecord.objects.filter(monthly_payment=payment).count(), 0)

    def test_electricity_is_included_once_in_ledger_and_dashboard_totals(self):
        room = Room.objects.create(
            number='G-109', building=self.building, room_type='single', price=7001,
        )
        guest = Guest.objects.create(
            first_name='Utility', last_name='Tenant', room=room,
            check_in_date=date.today(), is_active=True,
        )
        month = date.today().replace(day=1)
        payment = MonthlyPayment.objects.get(room=room)
        ElectricityBill.objects.create(
            room=room, guest=guest, month=month, starting_reading=10,
            ending_reading=20, units_consumed=10, rate_per_unit=8,
            bill_amount=Decimal('80.00'), paid_amount=Decimal('30.00'),
            due_date=date.today(),
        )
        payment.refresh_from_db()
        self.assertEqual(payment.get_total_amount_due(), Decimal('7081.00'))
        self.assertEqual(payment.get_total_remaining(), Decimal('7051.00'))

        response = self.client.get(reverse('performance_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_expected_rent'], 7001.0)
        self.assertEqual(response.context['total_expected_due'], 7081.0)
        self.assertEqual(response.context['total_collected'], 0.0)
        self.assertEqual(response.context['total_electricity_collected'], 30.0)
        self.assertEqual(response.context['total_electricity_expense'], 80.0)

        response = self.client.get(reverse('dashboard_metrics_api'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['metrics']['expected_yield'], 7001.0)
        self.assertEqual(response.json()['metrics']['expected_total_due'], 7081.0)
        self.assertEqual(response.json()['metrics']['realized_revenue'], 0.0)
        self.assertEqual(response.json()['metrics']['electricity_collected'], 30.0)
        self.assertEqual(response.json()['metrics']['electricity_expense'], 80.0)
        self.assertEqual(response.json()['metrics']['net_revenue'], -50.0)
