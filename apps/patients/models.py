from pathlib import Path
import uuid
from django.db import models
from .storage import protected_storage
from apps.shared.fields import EncryptedCharField, EncryptedTextField, compute_lookup_hash
from apps.patients.normalization import normalize_phone, normalize_email

def patient_document_upload_to(instance, filename):
    """Generate an opaque, collision-resistant storage key.

    Format: patients/<patient_id>/<document_type>/<uuid4hex>.<ext>
    Never exposes patient names, contact details, or original filenames
    in the storage paths."""
    patient_id = instance.patient_id or "unassigned"

    doc_type = getattr(instance, "document_type", "other")
    if doc_type not in {"insurance", "agreement", "consent", "id_copy", "other"}:
        doc_type = "other"

    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in {"pdf", "png", "jpg", "jpeg", "webp"}:
        ext = "bin"

    unique_id = uuid.uuid4().hex
    return f"patients/{patient_id}/{doc_type}/{unique_id}.{ext}"


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
    phone_lookup_hash = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        db_index=True,
    )
    email_lookup_hash = models.CharField(
        max_length=64,
        blank=True,
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
        norm_phone = normalize_phone(self.phone) if self.phone else ""
        norm_email = normalize_email(self.email) if self.email else ""

        self.phone_lookup_hash = compute_lookup_hash(norm_phone) if norm_phone else ""
        self.email_lookup_hash = compute_lookup_hash(norm_email) if norm_email else ""

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if "phone" in update_fields:
                update_fields.add("phone_lookup_hash")
            if "email" in update_fields:
                update_fields.add("email_lookup_hash")
            kwargs["update_fields"] = list(update_fields)

        super().save(*args, **kwargs)

        if not self.patient_code:
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
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        help_text="Sanitized original filename for staff display only; never used in storage paths.",
    )
    document_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_OTHER,
    )
    file = models.FileField(upload_to=patient_document_upload_to, storage=protected_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient"],
                condition=models.Q(document_type="insurance"),
                name="uniq_insurance_document_per_patient",
            ),
        ]


    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._original_file_name = instance.file.name if instance.file else None
        return instance

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            display_name = self.original_filename or Path(self.file.name).name or "Document"
            self.title = display_name[:150]
        super().save(*args, **kwargs)
        # Keep remembered file key in sync after successful persistence
        if self.file:
            self._original_file_name = self.file.name

    @property
    def filename(self):
        return self.original_filename or Path(self.file.name).name

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
