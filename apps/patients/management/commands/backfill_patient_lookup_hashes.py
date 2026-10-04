from django.core.management.base import BaseCommand
from django.db import connection
from apps.patients.models import Patient
from apps.patients.normalization import normalize_phone, normalize_email
from apps.shared.fields import compute_lookup_hash, FernetEncryptor, DecryptionError

class Command(BaseCommand):
    help = "Backfills phone_lookup_hash and email_lookup_hash for all existing patient records."

    def handle(self, *args, **options):
        # Query raw database values directly to prevent premature ORM model hydration crashes
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, phone, email FROM website_patient ORDER BY id")
            rows = cursor.fetchall()

        total = len(rows)
        phone_hashes = 0
        email_hashes = 0
        blank_phones = 0
        blank_emails = 0
        errors = 0

        self.stdout.write(f"Starting backfill for {total} patient records...")

        for patient_id, raw_phone, raw_email in rows:
            try:
                decrypted_phone = FernetEncryptor.decrypt(raw_phone) if raw_phone else ""
                decrypted_email = FernetEncryptor.decrypt(raw_email) if raw_email else ""
            except DecryptionError as e:
                errors += 1
                self.stderr.write(f"Decryption error for patient ID #{patient_id}: {e}")
                continue

            norm_phone = normalize_phone(decrypted_phone) if decrypted_phone else ""
            norm_email = normalize_email(decrypted_email) if decrypted_email else ""

            phone_hash = compute_lookup_hash(norm_phone) if norm_phone else ""
            email_hash = compute_lookup_hash(norm_email) if norm_email else ""

            if norm_phone:
                phone_hashes += 1
            else:
                blank_phones += 1

            if norm_email:
                email_hashes += 1
            else:
                blank_emails += 1

            Patient.objects.filter(pk=patient_id).update(
                phone_lookup_hash=phone_hash,
                email_lookup_hash=email_hash,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Patients processed: {total}\n"
            f"Phone hashes generated: {phone_hashes}\n"
            f"Email hashes generated: {email_hashes}\n"
            f"Blank phone values: {blank_phones}\n"
            f"Blank email values: {blank_emails}\n"
            f"Errors: {errors}"
        ))
