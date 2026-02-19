from datetime import date, time
from django.test import TestCase
from django.db import IntegrityError, transaction
from website.models import Appointment, Patient
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

    # Patient's Test Cases
    def test_patient_reused_by_phone(self):
        print("\n[TEST] patient reused by phone")

        service = APPOINTMENT_SERVICES[0]
        existing = Patient.objects.create(name="Old Name", phone="09171234567", email="old@test.com")

        form = AppointmentForm(data={
            "name": "New Name",
            "phone": "09171234567",   # same phone -> should reuse existing
            "email": "new@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(9, 0),
            "services": [service],
            "notes": "",
        })

        print("  - valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)
        print("  - existing patient id:", existing.id)
        print("  - appt.patient id:", appt.patient_id)

        self.assertEqual(appt.patient_id, existing.id)

    def test_patient_reused_by_email(self):
        print("\n[TEST] patient reused by email")

        service = APPOINTMENT_SERVICES[0]
        existing = Patient.objects.create(name="Old Name", phone="09000000000", email="same@test.com")

        form = AppointmentForm(data={
            "name": "Someone Else",
            "phone": "09179999999",     # different phone
            "email": "same@test.com",   # same email -> should reuse existing
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(10, 0),
            "services": [service],
            "notes": "",
        })

        print("  - valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)
        print("  - existing patient id:", existing.id)
        print("  - appt.patient id:", appt.patient_id)

        self.assertEqual(appt.patient_id, existing.id)

    def test_patient_created_when_no_match(self):
        print("\n[TEST] patient created when no match")

        service = APPOINTMENT_SERVICES[0]

        form = AppointmentForm(data={
            "name": "Brand New",
            "phone": "09991234567",
            "email": "brandnew@test.com",
            "appointment_date": date(2026, 2, 18),
            "appointment_time": time(11, 0),
            "services": [service],
            "notes": "",
        })

        print("  - valid?:", form.is_valid())
        if not form.is_valid():
            print("  - errors:", form.errors.as_text())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        appt = form.save(status=Appointment.STATUS_PENDING)
        print("  - appt.patient id:", appt.patient_id)

        self.assertIsNotNone(appt.patient_id)
        self.assertTrue(Patient.objects.filter(id=appt.patient_id).exists())

    # Database constraints test cases
    def test_db_unique_constraint_blocks_active_duplicate(self):
        print("\n[TEST] DB constraint blocks duplicate for pending/confirmed")

        Appointment.objects.create(
            name="A",
            phone="1",
            email="a@test.com",
            date=date(2026, 2, 18),
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
                    date=date(2026, 2, 18),
                    start_time=time(9, 0),
                    timeslot="9:00 AM",
                    status=Appointment.STATUS_CONFIRMED,
                    services=[APPOINTMENT_SERVICES[0]],
                )
            print("  - unexpected: DB allowed duplicate")
            self.fail("Expected IntegrityError but duplicate insert succeeded")
        except IntegrityError as e:
            print("  - got IntegrityError (expected):", str(e))

    def test_db_allows_if_existing_is_cancelled(self):
        print("\n[TEST] DB allows new active slot if existing is cancelled")

        Appointment.objects.create(
            name="Old",
            phone="1",
            email="old@test.com",
            date=date(2026, 2, 18),
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
            date=date(2026, 2, 18),
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_PENDING,
            services=[APPOINTMENT_SERVICES[0]],
        )

        print("  - created new appointment id:", a2.id)
        self.assertIsNotNone(a2.id)

