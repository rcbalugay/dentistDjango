import os
import shutil
import tempfile
from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError, connection
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from apps.patients.models import Patient, PatientDocument, AuditLog
from apps.patients.services import get_or_create_patient_record, save_patient_document
from apps.patients.selectors import (
    resolve_patient_identity,
    find_patient_by_phone,
    find_patient_by_email,
    PatientConflictError,
)
from apps.patients.storage import (
    ProtectedFileSystemStorage,
    ProtectedStorageProxy,
    get_protected_storage,
    protected_storage,
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
        from apps.staff.services.role_service import assign_staff_role, setup_roles_and_permissions
        setup_roles_and_permissions()
        self.staff_user = User.objects.create_user(username="staff", password="password", is_staff=True)
        assign_staff_role(self.staff_user, "Dentist")
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
        # Not logged in should redirect to login
        url = reverse("dashboard:download_patient_document", args=[self.document.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # Logged in but non-staff user receives 403
        client.login(username="patient", password="password")
        response = client.get(url)
        self.assertEqual(response.status_code, 403)

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


class ProtectedStorageAndProxyTests(TestCase):
    def test_get_protected_storage_returns_protected_backend(self):
        backend = get_protected_storage()
        self.assertIsInstance(backend, ProtectedFileSystemStorage)
    def test_direct_url_raises_not_implemented_error(self):
        with self.assertRaises(NotImplementedError):
            protected_storage.url("patients/1/insurance/test.pdf")
    def test_proxy_resolves_dynamically_under_override_settings(self):
        temp_dir = tempfile.mkdtemp()
        try:
            with override_settings(
                STORAGES={
                    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                    "protected": {
                        "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                        "OPTIONS": {"location": temp_dir},
                    },
                }
            ):
                self.assertEqual(protected_storage.base_location, temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
class PatientDocumentModelAndKeyTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(name="Storage Test Patient", phone="09170001122")
    def test_opaque_key_format_and_uuid(self):
        doc = PatientDocument.objects.create(
            patient=self.patient,
            document_type=PatientDocument.TYPE_INSURANCE,
            file=SimpleUploadedFile("my_real_card.pdf", b"test pdf content", content_type="application/pdf"),
        )
        self.assertTrue(doc.file.name.startswith(f"patients/{self.patient.id}/insurance/"))
        self.assertTrue(doc.file.name.endswith(".pdf"))
        # Verify original filename is NOT in storage key
        self.assertNotIn("my_real_card", doc.file.name)
        # Verify original filename is stored as metadata
        self.assertEqual(doc.original_filename, "")
    def test_unknown_document_type_and_extension_fallback(self):
        doc = PatientDocument.objects.create(
            patient=self.patient,
            document_type="unrecognized_type",
            file=SimpleUploadedFile("script.exe", b"binary content", content_type="application/octet-stream"),
        )
        # Type defaults to 'other' and extension defaults to 'bin'
        self.assertTrue(doc.file.name.startswith(f"patients/{self.patient.id}/other/"))
        self.assertTrue(doc.file.name.endswith(".bin"))
    def test_insurance_unique_constraint_enforced_in_postgresql(self):
        PatientDocument.objects.create(
            patient=self.patient,
            document_type=PatientDocument.TYPE_INSURANCE,
            file=SimpleUploadedFile("card1.pdf", b"card1 content"),
        )
        # Attempting to create a second active insurance document for the same patient must raise IntegrityError
        with self.assertRaises(IntegrityError):
            PatientDocument.objects.create(
                patient=self.patient,
                document_type=PatientDocument.TYPE_INSURANCE,
                file=SimpleUploadedFile("card2.pdf", b"card2 content"),
            )
class PatientDocumentLifecycleTests(TestCase):
    def setUp(self):
        self.temp_storage_dir = tempfile.mkdtemp()
        self.patient = Patient.objects.create(name="Lifecycle Patient", phone="09173334455")
    def tearDown(self):
        shutil.rmtree(self.temp_storage_dir, ignore_errors=True)
    def test_document_deletion_cleans_up_storage_file_on_commit(self):
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                "protected": {
                    "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                    "OPTIONS": {"location": self.temp_storage_dir},
                },
            }
        ):
            with self.captureOnCommitCallbacks(execute=True):
                doc = PatientDocument.objects.create(
                    patient=self.patient,
                    document_type=PatientDocument.TYPE_AGREEMENT,
                    file=SimpleUploadedFile("agreement.pdf", b"agreement content"),
                )
            file_path = os.path.join(self.temp_storage_dir, doc.file.name)
            self.assertTrue(os.path.exists(file_path))
            # Delete document and verify physical file is deleted upon commit
            with self.captureOnCommitCallbacks(execute=True):
                doc.delete()
            self.assertFalse(os.path.exists(file_path))
    def test_patient_cascade_deletion_cleans_up_document_files(self):
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                "protected": {
                    "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                    "OPTIONS": {"location": self.temp_storage_dir},
                },
            }
        ):
            with self.captureOnCommitCallbacks(execute=True):
                doc = PatientDocument.objects.create(
                    patient=self.patient,
                    document_type=PatientDocument.TYPE_AGREEMENT,
                    file=SimpleUploadedFile("doc.pdf", b"doc content"),
                )
            file_path = os.path.join(self.temp_storage_dir, doc.file.name)
            self.assertTrue(os.path.exists(file_path))
            # Delete the patient (cascading delete)
            with self.captureOnCommitCallbacks(execute=True):
                self.patient.delete()
            self.assertFalse(os.path.exists(file_path))
    def test_file_replacement_cleans_up_old_file_on_commit(self):
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                "protected": {
                    "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                    "OPTIONS": {"location": self.temp_storage_dir},
                },
            }
        ):
            with self.captureOnCommitCallbacks(execute=True):
                doc = PatientDocument.objects.create(
                    patient=self.patient,
                    document_type=PatientDocument.TYPE_AGREEMENT,
                    file=SimpleUploadedFile("initial.pdf", b"initial content"),
                )
            old_file_path = os.path.join(self.temp_storage_dir, doc.file.name)
            self.assertTrue(os.path.exists(old_file_path))
            # Replace file
            with self.captureOnCommitCallbacks(execute=True):
                doc.file = SimpleUploadedFile("replacement.pdf", b"replacement content")
                doc.save()
            new_file_path = os.path.join(self.temp_storage_dir, doc.file.name)
            self.assertTrue(os.path.exists(new_file_path))
            self.assertFalse(os.path.exists(old_file_path))
class PatientDocumentServiceTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(name="Service Patient", phone="09176667788")
    def test_save_patient_document_insurance_replacement(self):
        f1 = SimpleUploadedFile("card1.jpg", b"card1 image content")
        doc1 = save_patient_document(
            patient=self.patient,
            file=f1,
            title="Card 1",
            document_type=PatientDocument.TYPE_INSURANCE,
            original_filename="card1.jpg",
        )
        self.assertEqual(PatientDocument.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(doc1.original_filename, "card1.jpg")
        # Upload a second insurance document via save_patient_document
        f2 = SimpleUploadedFile("card2.jpg", b"card2 image content")
        doc2 = save_patient_document(
            patient=self.patient,
            file=f2,
            title="Card 2",
            document_type=PatientDocument.TYPE_INSURANCE,
            original_filename="card2.jpg",
        )
        # Verify only 1 active insurance record exists and it is doc2
        self.assertEqual(PatientDocument.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(PatientDocument.objects.get(patient=self.patient).id, doc2.id)
    def test_save_patient_document_non_insurance_does_not_replace(self):
        doc1 = save_patient_document(
            patient=self.patient,
            file=SimpleUploadedFile("agreement1.pdf", b"a1"),
            document_type=PatientDocument.TYPE_AGREEMENT,
        )
        doc2 = save_patient_document(
            patient=self.patient,
            file=SimpleUploadedFile("agreement2.pdf", b"a2"),
            document_type=PatientDocument.TYPE_AGREEMENT,
        )
        # Both agreements remain active
        self.assertEqual(PatientDocument.objects.filter(patient=self.patient).count(), 2)
class PatientDocumentManagementCommandTests(TestCase):
    def setUp(self):
        self.temp_media = tempfile.mkdtemp()
        self.temp_protected = tempfile.mkdtemp()
        self.patient = Patient.objects.create(name="Command Test Patient", phone="09178889900")
    def tearDown(self):
        shutil.rmtree(self.temp_media, ignore_errors=True)
        shutil.rmtree(self.temp_protected, ignore_errors=True)
    def test_migrate_documents_to_protected_copies_and_verifies(self):
        with override_settings(
            MEDIA_ROOT=self.temp_media,
            PROTECTED_MEDIA_ROOT=self.temp_protected,
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.temp_media},
                },
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                "protected": {
                    "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                    "OPTIONS": {"location": self.temp_protected},
                },
            },
        ):
            # Create a file in default (public media) storage
            default_storage = storages["default"]
            test_key = "patient_documents/99/test_record.pdf"
            default_storage.save(test_key, ContentFile(b"sample file for migration"))
            doc = PatientDocument.objects.create(
                patient=self.patient,
                document_type=PatientDocument.TYPE_OTHER,
                file=test_key,
            )
            # Run migration command with --copy
            call_command("migrate_documents_to_protected", "--copy")
            # Verify destination storage has the file
            dest_storage = storages["protected"]
            self.assertTrue(dest_storage.exists(test_key))
            # Verify source is still preserved when --delete-source was not passed
            self.assertTrue(default_storage.exists(test_key))
    def test_prune_orphaned_documents_command(self):
        with override_settings(
            PROTECTED_MEDIA_ROOT=self.temp_protected,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
                "protected": {
                    "BACKEND": "apps.patients.storage.ProtectedFileSystemStorage",
                    "OPTIONS": {"location": self.temp_protected},
                },
            },
        ):
            dest_storage = storages["protected"]
            orphan_key = "patients/99/other/orphan_test.pdf"
            dest_storage.save(orphan_key, ContentFile(b"orphan content"))
            # Dry run: file should NOT be deleted
            call_command("prune_orphaned_documents", "--min-age-minutes", "0")
            self.assertTrue(dest_storage.exists(orphan_key))
            # With --delete: file should be deleted
            call_command("prune_orphaned_documents", "--delete", "--min-age-minutes", "0")
            self.assertFalse(dest_storage.exists(orphan_key))