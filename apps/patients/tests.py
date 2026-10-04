from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError, connection
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.patients.models import Patient, PatientDocument, AuditLog
from apps.patients.services import get_or_create_patient_record
from apps.patients.selectors import (
    resolve_patient_identity,
    find_patient_by_phone,
    find_patient_by_email,
    PatientConflictError,
)
from apps.patients.normalization import normalize_phone, normalize_email
from apps.appointments.models import Appointment
from apps.shared.fields import compute_lookup_hash, DecryptionError, FernetEncryptor


class EncryptedLookupHashTests(TestCase):
    def test_lookup_hashes_computed_on_patient_creation(self):
        patient = Patient.objects.create(name="Lookup Test", phone="09171112233", email="lookup@test.com")
        self.assertTrue(patient.phone_lookup_hash)
        self.assertTrue(patient.email_lookup_hash)
        self.assertEqual(len(patient.phone_lookup_hash), 64)
        self.assertEqual(len(patient.email_lookup_hash), 64)
    def test_deterministic_hashing_same_input(self):
        h1 = compute_lookup_hash("09171112233")
        h2 = compute_lookup_hash("09171112233")
        self.assertEqual(h1, h2)
    def test_different_values_produce_different_hashes(self):
        h1 = compute_lookup_hash("09171112233")
        h2 = compute_lookup_hash("09179998877")
        self.assertNotEqual(h1, h2)
    def test_normalization_produces_identical_hash(self):
        h1 = compute_lookup_hash(normalize_phone("+63 917-123-4567"))
        h2 = compute_lookup_hash(normalize_phone("09171234567"))
        self.assertEqual(h1, h2)
    def test_indexed_lookup_by_phone_hash(self):
        patient = Patient.objects.create(name="Phone Match", phone="09171113333", email="p@match.com")
        found = Patient.objects.filter(phone_lookup_hash=patient.phone_lookup_hash).first()
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, patient.pk)
    def test_selector_find_patient_by_phone(self):
        patient = Patient.objects.create(name="Selector Phone", phone="09172223344", email="")
        found = find_patient_by_phone("+63 917-222-3344")
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, patient.pk)
    def test_selector_find_patient_by_email(self):
        patient = Patient.objects.create(name="Selector Email", phone="", email="selector@test.com")
        found = find_patient_by_email("SELECTOR@TEST.COM")
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, patient.pk)
    def test_hash_updates_when_phone_changes(self):
        patient = Patient.objects.create(name="Change Phone", phone="09171110000", email="c@test.com")
        old_hash = patient.phone_lookup_hash
        patient.phone = "09179990000"
        patient.save(update_fields=["phone"])
        patient.refresh_from_db()
        self.assertNotEqual(patient.phone_lookup_hash, old_hash)
        self.assertEqual(patient.phone_lookup_hash, compute_lookup_hash("09179990000"))
    def test_hash_updates_when_email_changes(self):
        patient = Patient.objects.create(name="Change Email", phone="09170001111", email="old@email.com")
        old_hash = patient.email_lookup_hash
        patient.email = "new@email.com"
        patient.save(update_fields=["email"])
        patient.refresh_from_db()
        self.assertNotEqual(patient.email_lookup_hash, old_hash)
        self.assertEqual(patient.email_lookup_hash, compute_lookup_hash("new@email.com"))
    def test_blank_values_result_in_blank_hashes(self):
        patient = Patient.objects.create(name="Blank Test", phone="", email="")
        self.assertEqual(patient.phone_lookup_hash, "")
        self.assertEqual(patient.email_lookup_hash, "")
    def test_invalid_ciphertext_raises_decryption_error(self):
        with self.assertRaises(DecryptionError):
            FernetEncryptor.decrypt("gAAAAABcorruptInvalidCiphertext1234567890=")
    def test_plain_text_input_to_decrypt_raises_decryption_error(self):
        with self.assertRaises(DecryptionError):
            FernetEncryptor.decrypt("plain-text-value")


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


class PatientIdentityResolutionTests(TestCase):
    def test_new_patient_creation(self):
        patient = get_or_create_patient_record(name="John Doe", phone="09171112233", email="john@example.com")
        self.assertIsNotNone(patient)
        self.assertEqual(patient.name, "John Doe")
        self.assertEqual(patient.phone, "09171112233")
        self.assertEqual(patient.email, "john@example.com")
    def test_creation_requires_at_least_one_contact_identifier(self):
        patient = get_or_create_patient_record(name="Ghost Patient", phone="", email="")
        self.assertIsNone(patient)
        self.assertEqual(Patient.objects.filter(name="Ghost Patient").count(), 0)
    def test_existing_patient_by_phone(self):
        original = Patient.objects.create(name="Alice", phone="09170001111", email="alice@test.com")
        resolved = resolve_patient_identity(phone="09170001111", email="")
        self.assertEqual(resolved.pk, original.pk)
    def test_existing_patient_by_email(self):
        original = Patient.objects.create(name="Bob", phone="09170002222", email="bob@test.com")
        resolved = resolve_patient_identity(phone="", email="bob@test.com")
        self.assertEqual(resolved.pk, original.pk)
    def test_existing_patient_by_both_identifiers(self):
        original = Patient.objects.create(name="Charlie", phone="09170003333", email="charlie@test.com")
        resolved = resolve_patient_identity(phone="09170003333", email="charlie@test.com")
        self.assertEqual(resolved.pk, original.pk)
    def test_phone_and_email_conflict_raises_error(self):
        p1 = Patient.objects.create(name="Patient One", phone="09171111111", email="one@test.com")
        p2 = Patient.objects.create(name="Patient Two", phone="09172222222", email="two@test.com")
        with self.assertRaises(PatientConflictError):
            resolve_patient_identity(phone="09171111111", email="two@test.com")
    def test_conflict_exception_does_not_leak_patient_ids(self):
        p1 = Patient.objects.create(name="Patient One", phone="09171111111", email="one@test.com")
        p2 = Patient.objects.create(name="Patient Two", phone="09172222222", email="two@test.com")
        with self.assertRaises(PatientConflictError) as cm:
            resolve_patient_identity(phone="09171111111", email="two@test.com")
        error_message = str(cm.exception)
        self.assertNotIn(str(p1.pk), error_message)
        self.assertNotIn(str(p2.pk), error_message)
    def test_phone_formatting_normalization(self):
        original = Patient.objects.create(name="Diana", phone="09171234567", email="diana@test.com")
        resolved = resolve_patient_identity(phone="+63 917-123-4567", email="diana@test.com")
        self.assertEqual(resolved.pk, original.pk)
    def test_email_case_normalization(self):
        original = Patient.objects.create(name="Edward", phone="09173334444", email="edward@test.com")
        resolved = resolve_patient_identity(phone="09173334444", email="EDWARD@TEST.COM")
        self.assertEqual(resolved.pk, original.pk)
    def test_sequential_duplicate_submission_reuses_patient(self):
        p1 = get_or_create_patient_record(name="Frank", phone="09175556666", email="frank@test.com")
        p2 = get_or_create_patient_record(name="Frank", phone="09175556666", email="frank@test.com")
        self.assertEqual(p1.pk, p2.pk)
        self.assertEqual(Patient.objects.count(), 1)
    def test_existing_patient_does_not_overwrite_populated_phone(self):
        original = Patient.objects.create(name="Grace", phone="09171110000", email="grace@test.com")
        updated = get_or_create_patient_record(name="Grace", phone="09179999999", email="grace@test.com")
        original.refresh_from_db()
        self.assertEqual(original.phone, "09171110000")
    def test_existing_patient_does_not_overwrite_populated_email(self):
        original = Patient.objects.create(name="Henry", phone="09172220000", email="henry@test.com")
        # Submitting matching phone with a different email should not overwrite Henry's existing email
        updated = get_or_create_patient_record(name="Henry", phone="09172220000", email="newhenry@test.com")
        original.refresh_from_db()
        self.assertEqual(original.email, "henry@test.com")
    def test_existing_patient_fills_missing_phone(self):
        original = Patient.objects.create(name="Iris", phone="", email="iris@test.com")
        updated = get_or_create_patient_record(name="Iris", phone="09173330000", email="iris@test.com")
        original.refresh_from_db()
        self.assertEqual(original.phone, "09173330000")
    def test_existing_patient_fills_missing_email(self):
        original = Patient.objects.create(name="Jack", phone="09174440000", email="")
        updated = get_or_create_patient_record(name="Jack", phone="09174440000", email="jack@test.com")
        original.refresh_from_db()
        self.assertEqual(original.email, "jack@test.com")


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
