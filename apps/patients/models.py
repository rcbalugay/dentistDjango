from django.db import models


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
