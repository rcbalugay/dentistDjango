from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.appointments.constants import APPOINTMENT_SERVICES


class AppointmentViewSmokeTests(TestCase):
    def next_weekday(self, weekday: int):
        today = timezone.localdate()
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    def next_open_date(self):
        return self.next_weekday(2)  # Wednesday

    def test_appointment_form_page_loads(self):
        response = self.client.get(reverse("appointment_form"))
        self.assertEqual(response.status_code, 200)

    def test_appointment_status_page_loads(self):
        response = self.client.get(reverse("appointment_status"))
        self.assertEqual(response.status_code, 200)

    def test_appointment_status_finds_existing_appointment(self):
        appointment = Appointment.objects.create(
            name="Tracked Patient",
            phone="09170000111",
            email="tracked@test.com",
            date=self.next_open_date(),
            timeslot="10:00 AM",
            appointment_code="APT-000123",
            services=[APPOINTMENT_SERVICES[0]],
            status=Appointment.STATUS_PENDING,
        )

        response = self.client.get(
            reverse("appointment_status"),
            {"code": appointment.appointment_code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, appointment.appointment_code)

    def test_appointment_status_shows_error_for_unknown_code(self):
        response = self.client.get(
            reverse("appointment_status"),
            {"code": "APT-DOES-NOT-EXIST"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No appointment was found for that appointment ID.")

    def test_valid_public_booking_redirects_and_creates_pending_appointment(self):
        booking_date = self.next_open_date()

        response = self.client.post(
            reverse("appointment_form"),
            {
                "name": "Smoke Test Patient",
                "phone": "09170000123",
                "email": "smoke@test.com",
                "appointment_date": booking_date.isoformat(),
                "appointment_time": "10:00",
                "services": [APPOINTMENT_SERVICES[0]],
                "notes": "Created by smoke test",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Appointment.objects.filter(email="smoke@test.com").exists()
        )

        appointment = Appointment.objects.get(email="smoke@test.com")
        self.assertEqual(appointment.status, Appointment.STATUS_PENDING)
        self.assertTrue(appointment.appointment_code)
