from django.db import models
from django.db.models import Q


class Appointment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
    )

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    services = models.JSONField(default=list)
    date = models.DateField()
    timeslot = models.CharField(max_length=40)
    start_time = models.TimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    appointment_code = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        db_index=True,
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    class Meta:
        indexes = [
            models.Index(fields=["date"], name="website_app_date_965bb0_idx"),
            models.Index(fields=["name"], name="website_app_name_7177d6_idx"),
            models.Index(fields=["patient"], name="website_app_patient_aa7552_idx"),
        ]
        ordering = ["-date", "start_time", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "start_time"],
                condition=Q(status__in=["pending", "confirmed"]),
                name="unique_active_appointment_per_timeslot",
            )
        ]
        db_table = "website_appointment"

    def initials(self):
        name = (self.name or "").strip()
        if not name:
            return ""

        parts = name.split()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.appointment_code:
            return

        self.appointment_code = f"APT-{self.pk:06d}"
        super().save(update_fields=["appointment_code"])

    def __str__(self):
        t = self.start_time.strftime("%I:%M %p").lstrip("0") if self.start_time else self.timeslot
        return f"{self.name} - {self.date} {t}"
