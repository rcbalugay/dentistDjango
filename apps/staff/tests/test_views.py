from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.appointments.models import Appointment

# Create your tests here.
@override_settings(WEATHERAPI_KEY="", SECURE_SSL_REDIRECT=False)
class DashboardAccessSmokeTests(TestCase):
    def next_weekday(self, weekday: int):
        today = timezone.localdate()
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("staff", password="pass12345", is_staff=True)
        self.user = User.objects.create_user("user", password="pass12345", is_staff=False)
        self.protected_urls = [
            reverse("dashboard:home"),
            reverse("dashboard:appointments"),
            reverse("dashboard:patients"),
        ]

    def test_protected_pages_require_login(self):
        for url in self.protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("dashboard:login"), response.url)

    def test_non_staff_is_rejected(self):
        self.client.login(username="user", password="pass12345")
        for url in self.protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("dashboard:login"), response.url)

    def test_staff_can_access(self):
        self.client.login(username="staff", password="pass12345")
        for url in self.protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_staff_created_appointment_is_confirmed(self):
        self.client.login(username="staff", password="pass12345")
        booking_date = self.next_weekday(2)  # Wednesday

        response = self.client.post(
            reverse("dashboard:appointments_form"),
            {
                "name": "Staff Booked Patient",
                "phone": "09170000020",
                "email": "staffbooked@test.com",
                "appointment_date": booking_date.isoformat(),
                "appointment_time": "10:00",
                "services": ["Consultation"],
                "notes": "Booked by staff",
            },
        )

        self.assertEqual(response.status_code, 302)

        appt = Appointment.objects.get(email="staffbooked@test.com")
        self.assertEqual(appt.status, Appointment.STATUS_CONFIRMED)
