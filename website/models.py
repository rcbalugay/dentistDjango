from django.db import models

# Create your models here.
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

	name = models.CharField(max_length=120)
	phone = models.CharField(max_length=40)
	email = models.EmailField(blank=True)
	# stores selected service
	services = models.JSONField(default=list)
	date = models.DateField()
	timeslot = models.CharField(max_length=40)

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
		]
		ordering = ["-date", "timeslot", "name"]

	def __str__(self):
		return f"{self.name} — {self.date} {self.timeslot}" 