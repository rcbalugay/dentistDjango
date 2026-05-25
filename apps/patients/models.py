from pathlib import Path
from django.db import models
from .storage import protected_storage
from apps.shared.fields import EncryptedCharField, EncryptedTextField

def patient_document_upload_to(instance, filename):
    return f"patient_documents/{instance.patient_id}/{filename}"


class Patient(models.Model):
    name = models.CharField(max_length=120)
    phone = EncryptedCharField(max_length=255, blank=True)
    email = EncryptedCharField(max_length=255, blank=True)
    notes = EncryptedTextField(blank=True, null=True)
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
    file = models.FileField(upload_to=patient_document_upload_to, storage=protected_storage)
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


class AuditLog(models.Model):
    ACTION_VIEW = "view"
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_VIEW, "View"),
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        db_table = "website_auditlog"

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"{self.timestamp} - {user_str} - {self.action} - {self.model_name}"
