from pathlib import Path

from django.db import models


def patient_document_upload_to(instance, filename):
    return f"patient_documents/{instance.patient_id}/{filename}"


class Patient(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    patient_code = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="website_pat_name_d318b7_idx"),
            models.Index(fields=["phone"], name="website_pat_phone_6e57b7_idx"),
            models.Index(fields=["email"], name="website_pat_email_148a3f_idx"),
        ]
        db_table = "website_patient"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.patient_code:
            return

        self.patient_code = f"PAT-{self.pk:06d}"
        super().save(update_fields=["patient_code"])

    def __str__(self):
        contact = self.phone or self.email or "no contact"
        return f"{self.name} ({contact})"


class PatientDocument(models.Model):
    TYPE_INSURANCE = "insurance"
    TYPE_AGREEMENT = "agreement"
    TYPE_CONSENT = "consent"
    TYPE_ID = "id_copy"
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_INSURANCE, "Insurance Image"),
        (TYPE_AGREEMENT, "Agreement Document"),
        (TYPE_CONSENT, "Consent Form"),
        (TYPE_ID, "ID Copy"),
        (TYPE_OTHER, "Other"),
    ]

    patient = models.ForeignKey(
        Patient,
        related_name="documents",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=150, blank=True)
    document_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_OTHER,
    )
    file = models.FileField(upload_to=patient_document_upload_to)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            self.title = Path(self.file.name).name
        super().save(*args, **kwargs)

    @property
    def filename(self):
        return Path(self.file.name).name

    @property
    def is_image(self):
        return Path(self.file.name).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    def __str__(self):
        return f"{self.patient.name} - {self.title or self.filename}"
