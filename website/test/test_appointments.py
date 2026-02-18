from datetime import date, time
from django.test import TestCase
from website.models import Appointment
from website.forms import AppointmentForm

class AppointmentFormTests(TestCase):
    def test_double_booking_if_pend_cfrm(self):
        print("\n[TEST] double booking is blocked for pending/confirmed")
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=date(2026, 2, 18),
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=["Whitening"],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": "2026-02-18",
            "appointment_time": "10:00",
            "services": ["Consultation"],
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertFalse(form.is_valid())
        self.assertTrue(
            any("already booked" in err.lower() for err in form.non_field_errors())
        )

    def test_allow_booking_if_exist_cancelled_or_completed(self):
        print("\n[TEST] cancelled/completed does NOT block booking")

        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=date(2026, 2, 18),
            start_time=time(11, 0),
            timeslot="11:00 AM",
            status=Appointment.STATUS_CANCELLED,
            services=["Therapy"],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": "2026-02-18",
            "appointment_time": "11:00",
            "services": ["Surgery"],
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())