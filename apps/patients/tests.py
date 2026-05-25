from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError, connection
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.patients.models import Patient, PatientDocument, AuditLog
from apps.appointments.models import Appointment

class PatientFieldEncryptionTests(TestCase):
    def test_field_encryption_at_rest(self):
        # Create patient record
        patient = Patient.objects.create(
            name="Secure Patient",
            phone="09171234567",
            email="secure@patient.com",
            notes="Extremely confidential HIPAA information"
        )
        
        # Verify model transparently decrypts
        self.assertEqual(patient.phone, "09171234567")
        self.assertEqual(patient.email, "secure@patient.com")
        self.assertEqual(patient.notes, "Extremely confidential HIPAA information")
        
        # Verify raw SQL database values are encrypted ciphertexts (starting with 'gAAAA')
        with connection.cursor() as cursor:
            cursor.execute("SELECT phone, email, notes FROM website_patient WHERE id = %s", [patient.id])
            row = cursor.fetchone()
            
            raw_phone, raw_email, raw_notes = row
            
            # Check phone raw value is encrypted
            self.assertTrue(raw_phone.startswith("gAAAA"))
            self.assertNotEqual(raw_phone, "09171234567")
            
            # Check email raw value is encrypted
            self.assertTrue(raw_email.startswith("gAAAA"))
            self.assertNotEqual(raw_email, "secure@patient.com")
            
            # Check notes raw value is encrypted
            self.assertTrue(raw_notes.startswith("gAAAA"))
            self.assertNotEqual(raw_notes, "Extremely confidential HIPAA information")

class PatientDocumentProtectedStorageAndDownloadTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.regular_user = User.objects.create_user(username="patient", password="password", is_staff=False)
        self.patient = Patient.objects.create(name="Jane Doe", phone="09171234567", email="jane@doe.com")
        
        # Create a patient document
        dummy_file = SimpleUploadedFile("insurance.pdf", b"pdf_content", content_type="application/pdf")
        self.document = PatientDocument.objects.create(
            patient=self.patient,
            title="Insurance Card",
            document_type=PatientDocument.TYPE_INSURANCE,
            file=dummy_file
        )

    def test_unauthorized_download_redirects_or_denies(self):
        client = Client()
        # Not logged in should redirect to login or deny
        url = reverse("dashboard:download_patient_document", args=[self.document.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirects to login
        
        # Logged in but non-staff user should deny with 403 or redirect
        client.login(username="patient", password="password")
        response = client.get(url)
        self.assertEqual(response.status_code, 302)  # staff_only decorator redirects to login by default if not staff

    def test_authorized_download_succeeds(self):
        client = Client()
        client.login(username="staff", password="password")
        url = reverse("dashboard:download_patient_document", args=[self.document.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "application/pdf")

class SchedulingConcurrencyTests(TestCase):
    def test_concurrency_collision_integrity_error(self):
        # We try to create two active appointments at the exact same timeslot
        booking_date = date.today() + timedelta(days=5)
        
        # Create first confirmed appointment
        Appointment.objects.create(
            name="First Patient",
            phone="09171234567",
            email="first@patient.com",
            date=booking_date,
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CONFIRMED,
        )
        
        # Second appointment at the same slot should raise IntegrityError due to UniqueConstraint
        with self.assertRaises(IntegrityError):
            Appointment.objects.create(
                name="Second Patient",
                phone="09179998888",
                email="second@patient.com",
                date=booking_date,
                start_time=time(10, 0),
                timeslot="10:00 AM",
                status=Appointment.STATUS_CONFIRMED,
            )

class AuditLogSignalsTests(TestCase):
    def test_patient_signals_creates_audit_log(self):
        # Clearing existing log records to isolate this test
        AuditLog.objects.all().delete()
        
        # Create a patient
        patient = Patient.objects.create(
            name="Audited Patient",
            phone="09171234567",
            email="audited@patient.com"
        )
        
        # Verify AuditLog created for patient creation
        logs = AuditLog.objects.filter(model_name="Patient", object_id=patient.id)
        self.assertTrue(logs.exists())
        self.assertEqual(logs.first().action, AuditLog.ACTION_CREATE)
