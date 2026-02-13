from django.db import models
from django.db.models import Q

# Create your models here.
class Patient(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True, null=True)      # optional general notes about the patient
    created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		ordering = ["name"]
		indexes = [
			models.Index(fields=["name"]),
			models.Index(fields=["phone"]),
			models.Index(fields=["email"]),
		]

    def __str__(self):
        contact = self.phone or self.email or "no contact"
        return f"{self.name} ({contact})"

class Appointment(models.Model):
	STATUS_PENDING   = "pending"
	STATUS_CONFIRMED = "confirmed"
	STATUS_CANCELLED = "cancelled"
	STATUS_COMPLETED = "completed"

	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_CONFIRMED, "Confirmed"),
		(STATUS_CANCELLED, "Cancelled"),
		(STATUS_COMPLETED, "Completed"),
	]

	# Links to Patient model in future updates
	patient = models.ForeignKey(
		Patient,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="appointments",
	)

	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=40, blank=True)
	email = models.EmailField(blank=True)
	# stores selected service
	services = models.JSONField(default=list)
	date = models.DateField()
	timeslot = models.CharField(max_length=40)
	start_time = models.TimeField(null=True, blank=True)

	notes = models.TextField(blank=True) # for staff notes
	created_at = models.DateTimeField(auto_now_add=True)

	status = models.CharField(
		max_length=10,
		choices=STATUS_CHOICES,
		default=STATUS_PENDING,
	)

	class Meta:
		indexes = [
			models.Index(fields=["date"]),
			models.Index(fields=["name"]),
			models.Index(fields=["patient"]),
		]
		ordering = ["-date", "start_time", "name"]

		constraints = [
			models.UniqueConstraint(
				fields=["date", "start_time"],
				condition=Q(status__in=["pending", "confirmed"]),
				name="unique_active_appointment_per_timeslot",
			)
		]

	def initials(self):
		"""
        Return 2-letter initials for use in the avatar circle.
        - If only one word: first two letters (e.g. 'F' → 'F', 'Anna' → 'AN')
        - If multiple words: first letter of first + first letter of last (e.g. 'Ricci Balugay' → 'RB')
        """
		name = (self.name or "").strip()
		if not name:
			return ""

		parts = name.split()
		if len(parts) == 1:
			return parts[0][:2].upper()
		return (parts[0][0] + parts[-1][0]).upper()

	def __str__(self):
		t = self.start_time.strftime("%I:%M %p").lstrip("0") if self.start_time else self.timeslot
		return f"{self.name} — {self.date} {t}"