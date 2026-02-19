from datetime import date, time
from django.test import TestCase
from website.models import Appointment
from website.forms import AppointmentForm
from website.constants import APPOINTMENT_SERVICES

class AppointmentFormTests(TestCase):
    def test_double_booking_if_pend_cfrm(self):
        print("\n[TEST] double booking is blocked for pending/confirmed")

        service = APPOINTMENT_SERVICES[1]
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=date(2026, 2, 18),
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=[service],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertFalse(form.is_valid())
        self.assertTrue(
            any("already booked" in err.lower() for err in form.non_field_errors()),
            list(form.non_field_errors()),
        )

    def test_allow_booking_if_exist_cancelled_or_completed(self):
        print("\n[TEST] cancelled/completed does NOT block booking")

        service = APPOINTMENT_SERVICES[2]
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=date(2026, 2, 18),
            start_time=time(11, 0),
            timeslot="11:00 AM",
            status=Appointment.STATUS_CANCELLED,
            services=[service],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(11, 0),
            "services": [service],
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_edit_same_appointment_does_not_self_collide(self):
        print("\n[TEST] editing the same appointment should not self-collide")

        service = APPOINTMENT_SERVICES[3]
        appt = Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="c@test.com",
            date=date(2026, 2, 18),
            start_time=time(12, 0),
            timeslot="12:00 PM",
            status=Appointment.STATUS_CONFIRMED,
            services=[service],
        )

        form = AppointmentForm(
            data={
                "name": "Existing Patient",
                "phone": "1234567890",
                "email": "c@test.com",
                "appointment_date": date(2026, 2, 18),
                "appointment_time": time(12, 0),
                "services": [service],
                "notes": "updated",
            },
            instance=appt,
        )

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_completed_does_not_block_booking(self):
        print("\n[TEST] completed status does NOT block booking")

        service = APPOINTMENT_SERVICES[0]
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="d@test.com",
            date=date(2026, 2, 18),
            start_time=time(13, 0),
            timeslot="1:00 PM",
            status=Appointment.STATUS_COMPLETED,
            services=[service],
        )

        form = AppointmentForm(
            data={
                "name": "New Patient",
                "phone": "0987654321",
                "email": "d@test.com",
                "appointment_date": date(2026, 2, 18),
                "appointment_time": time(13, 0),
                "services": [service],
                "notes": "",
            }
        )

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_save_sets_start_time_and_timeslot_format(self):
        print("\n[TEST] saving an appointment sets start_time and timeslot format")
     
        service = APPOINTMENT_SERVICES[0]
        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "e@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(14, 0),
            "services": [service],
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        print("  - saved appointment for start_time:", appt.start_time)
        print("  - saved appointment for timeslot:", appt.timeslot)
        print("  - saved appointment date:", appt.date)

        self.assertEqual(appt.date, date(2026, 2, 18))
        self.assertEqual(appt.start_time, time(14, 0))
        self.assertEqual(appt.timeslot, "2:00 PM")

    def test_services_are_normalized_unique_sorted(self):
        print("\n[TEST] services are normalized (trimmed/unique/sorted)")

        s1 = APPOINTMENT_SERVICES[0]
        s2 = APPOINTMENT_SERVICES[1] if len(APPOINTMENT_SERVICES) > 1 else APPOINTMENT_SERVICES[0]

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "456",
            "email": "f@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(10, 0),
            "services": [s2, s1, s1, s2],  # duplicates + whitespace
            "notes": "",
        })

        print("  - is the form valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
            print("  - non_field_errors:", list(form.non_field_errors()))

        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        expected = sorted({s1.strip(), s2.strip()})
        print("  - saved services:", appt.services)
        print("  - expected services:", expected)

        self.assertEqual(appt.services, expected)