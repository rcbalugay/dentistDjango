from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from django.test import TestCase
from django.db import IntegrityError, transaction
from website.models import Appointment, Patient
from apps.appointments.forms import AppointmentForm, StaffAppointmentForm
from apps.appointments.constants import APPOINTMENT_SERVICES

class AppointmentFormTests(TestCase):
    def next_weekday(self, weekday: int):
        today = timezone.localdate()
        days_ahead = (weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    def next_open_date(self):
        return self.next_weekday(2)  # Wednesday

    def next_closed_date(self):
        return self.next_weekday(1)  # Tuesday

    def test_double_booking_if_pend_cfrm(self):

        service = APPOINTMENT_SERVICES[1]
        booking_date = self.next_open_date()
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=booking_date,
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=[service],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertTrue(
            any("already booked" in err.lower() for err in form.non_field_errors()),
            list(form.non_field_errors()),
        )

    def test_allow_booking_if_exist_cancelled_or_completed(self):

        service = APPOINTMENT_SERVICES[2]
        booking_date = self.next_open_date()
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="a@test.com",
            date=booking_date,
            start_time=time(11, 0),
            timeslot="11:00 AM",
            status=Appointment.STATUS_CANCELLED,
            services=[service],
        )

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "b@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(11, 0),
            "services": [service],
            "notes": "",
        })


        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_edit_same_appointment_does_not_self_collide(self):

        service = APPOINTMENT_SERVICES[3]
        booking_date = self.next_open_date()
        appt = Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="c@test.com",
            date=booking_date,
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
                "appointment_date": booking_date,
                "appointment_time": time(12, 0),
                "services": [service],
                "notes": "updated",
            },
            instance=appt,
        )


        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_completed_does_not_block_booking(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()
        Appointment.objects.create(
            name="Existing Patient",
            phone="1234567890",
            email="d@test.com",
            date=booking_date,
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
                "appointment_date": booking_date,
                "appointment_time": time(13, 0),
                "services": [service],
                "notes": "",
            }
        )


        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_save_sets_start_time_and_timeslot_format(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()
        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "0987654321",
            "email": "e@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(14, 0),
            "services": [service],
            "notes": "",
        })


        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)


        self.assertEqual(appt.date, booking_date)
        self.assertEqual(appt.start_time, time(14, 0))
        self.assertEqual(appt.timeslot, "2:00 PM")

    def test_services_are_normalized_unique_sorted(self):

        s1 = APPOINTMENT_SERVICES[0]
        s2 = APPOINTMENT_SERVICES[1] if len(APPOINTMENT_SERVICES) > 1 else APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "New Patient",
            "phone": "09170000006",
            "email": "f@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(10, 0),
            "services": [s2, s1, s1, s2],  # duplicates + whitespace
            "notes": "",
        })


        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        expected = sorted({s1.strip(), s2.strip()})

        self.assertEqual(appt.services, expected)

    # Patient's Test Cases
    def test_patient_reused_by_phone(self):

        service = APPOINTMENT_SERVICES[0]
        existing = Patient.objects.create(name="Old Name", phone="09171234567", email="old@test.com")
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "New Name",
            "phone": "09171234567",   # same phone -> should reuse existing
            "email": "new@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(9, 0),
            "services": [service],
            "notes": "",
        })

        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        self.assertEqual(appt.patient_id, existing.id)

    def test_patient_reused_by_email(self):

        service = APPOINTMENT_SERVICES[0]
        existing = Patient.objects.create(name="Old Name", phone="09000000000", email="same@test.com")
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "Someone Else",
            "phone": "09179999999",     # different phone
            "email": "same@test.com",   # same email -> should reuse existing
            "appointment_date": booking_date,
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })

        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        self.assertEqual(appt.patient_id, existing.id)

    def test_patient_created_when_no_match(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "Brand New",
            "phone": "09991234567",
            "email": "brandnew@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(11, 0),
            "services": [service],
            "notes": "",
        })

        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)

        self.assertIsNotNone(appt.patient_id)
        self.assertTrue(Patient.objects.filter(id=appt.patient_id).exists())

    # Database constraints test cases
    def test_db_unique_constraint_blocks_active_duplicate(self):

        booking_date = self.next_open_date()
        Appointment.objects.create(
            name="A",
            phone="1",
            email="a@test.com",
            date=booking_date,
            start_time=time(9, 0),
            timeslot="9:00 AM",
            status=Appointment.STATUS_PENDING,
            services=[APPOINTMENT_SERVICES[0]],
        )

        try:
            with transaction.atomic():
                Appointment.objects.create(
                    name="B",
                    phone="2",
                    email="b@test.com",
                    date=booking_date,
                    start_time=time(9, 0),
                    timeslot="9:00 AM",
                    status=Appointment.STATUS_CONFIRMED,
                    services=[APPOINTMENT_SERVICES[0]],
                )
            self.fail("Expected IntegrityError but duplicate insert succeeded")
        except IntegrityError:
            pass

    def test_db_allows_if_existing_is_cancelled(self):

        booking_date = self.next_open_date()
        Appointment.objects.create(
            name="Old",
            phone="1",
            email="old@test.com",
            date=booking_date,
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CANCELLED,
            services=[APPOINTMENT_SERVICES[0]],
        )

        # should succeed (cancelled is not in the active constraint condition)
        a2 = Appointment.objects.create(
            name="New",
            phone="2",
            email="new@test.com",
            date=booking_date,
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_PENDING,
            services=[APPOINTMENT_SERVICES[0]],
        )

        self.assertIsNotNone(a2.id)

    def test_reject_past_date(self):

        service = APPOINTMENT_SERVICES[0]
        past_date = timezone.localdate() - timedelta(days=1)

        form = AppointmentForm(data={
            "name": "Past Patient",
            "phone": "09170000001",
            "email": "past@test.com",
            "appointment_date": past_date,
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertIn("appointment_date", form.errors)

    def test_reject_closed_day(self):

        service = APPOINTMENT_SERVICES[0]
        closed_date = self.next_closed_date()

        form = AppointmentForm(data={
            "name": "Closed Day Patient",
            "phone": "09170000002",
            "email": "closed@test.com",
            "appointment_date": closed_date,
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertIn("appointment_date", form.errors)

    def test_reject_time_outside_clinic_hours(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "Off Hours Patient",
            "phone": "09170000003",
            "email": "offhours@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(3, 0),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertIn("appointment_time", form.errors)

    def test_reject_time_not_on_the_hour(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "Half Hour Patient",
            "phone": "09170000004",
            "email": "half@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(10, 30),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertIn("appointment_time", form.errors)

    def test_allow_valid_future_open_slot(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        form = AppointmentForm(data={
            "name": "Valid Patient",
            "phone": "09170000005",
            "email": "valid@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })


        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_reject_holiday_on_open_day(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()

        with patch("apps.appointments.forms.CLINIC_HOLIDAYS", {booking_date: "Clinic Maintenance Day"}):
            form = AppointmentForm(data={
                "name": "Holiday Patient",
                "phone": "09170000006",
                "email": "holiday@test.com",
                "appointment_date": booking_date,
                "appointment_time": time(10, 0),
                "services": [service],
                "notes": "",
            })


            self.assertFalse(form.is_valid())
            self.assertIn("appointment_date", form.errors)
            self.assertTrue(
                any("Clinic Maintenance Day" in err for err in form.errors["appointment_date"]),
                form.errors["appointment_date"],
            )

    def test_reject_same_day_within_cutoff_window(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()
        simulated_now = timezone.make_aware(
            datetime.combine(booking_date, time(9, 30)),
            timezone.get_current_timezone(),
        )

        with (
            patch("apps.appointments.forms.timezone.localdate", return_value=booking_date),
            patch("apps.appointments.forms.timezone.now", return_value=simulated_now),
            patch("apps.appointments.forms.CLINIC_HOLIDAYS", {}),
        ):
            form = AppointmentForm(data={
                "name": "Cutoff Patient",
                "phone": "09170000007",
                "email": "cutoff@test.com",
                "appointment_date": booking_date,
                "appointment_time": time(11, 0),
                "services": [service],
                "notes": "",
            })


            self.assertFalse(form.is_valid())
            self.assertIn("appointment_time", form.errors)
            self.assertTrue(
                any("at least" in err.lower() for err in form.errors["appointment_time"]),
                form.errors["appointment_time"],
            )

    def test_allow_same_day_outside_cutoff_window(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_open_date()
        simulated_now = timezone.make_aware(
            datetime.combine(booking_date, time(9, 30)),
            timezone.get_current_timezone(),
        )

        with (
            patch("apps.appointments.forms.timezone.localdate", return_value=booking_date),
            patch("apps.appointments.forms.timezone.now", return_value=simulated_now),
            patch("apps.appointments.forms.CLINIC_HOLIDAYS", {}),
        ):
            form = AppointmentForm(data={
                "name": "Allowed Same Day",
                "phone": "09170000008",
                "email": "allowed-same-day@test.com",
                "appointment_date": booking_date,
                "appointment_time": time(12, 0),
                "services": [service],
                "notes": "",
            })


            self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_staff_form_allows_closed_day_and_off_hours(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_closed_date()

        form = StaffAppointmentForm(data={
            "name": "Staff Exception",
            "phone": "09170000009",
            "email": "staff-exception@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(3, 0),
            "services": [service],
            "notes": "",
        })


        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_staff_form_still_blocks_slot_collision(self):

        service = APPOINTMENT_SERVICES[0]
        booking_date = self.next_closed_date()
        Appointment.objects.create(
            name="Existing Staff Slot",
            phone="09170000010",
            email="existing-staff@test.com",
            date=booking_date,
            start_time=time(3, 0),
            timeslot="3:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=[service],
        )

        form = StaffAppointmentForm(data={
            "name": "New Staff Slot",
            "phone": "09170000011",
            "email": "new-staff@test.com",
            "appointment_date": booking_date,
            "appointment_time": time(3, 0),
            "services": [service],
            "notes": "",
        })


        self.assertFalse(form.is_valid())
        self.assertTrue(
            any("already booked" in err.lower() for err in form.non_field_errors()),
            list(form.non_field_errors()),
        )

