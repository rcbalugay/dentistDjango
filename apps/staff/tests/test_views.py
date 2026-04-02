import os
import shutil
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.appointments.models import Appointment
from apps.patients.models import Patient, PatientDocument
from apps.public.models import SiteContent

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
            reverse("dashboard:inquiries"),
            reverse("dashboard:website"),
            reverse("dashboard:settings"),
            reverse("dashboard:profile"),
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

    def test_legacy_message_and_blog_routes_redirect_to_new_pages(self):
        self.client.login(username="staff", password="pass12345")

        response = self.client.get(reverse("dashboard:message"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:inquiries"))

        response = self.client.get(reverse("dashboard:blog"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:website"))

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


@override_settings(WEATHERAPI_KEY="", SECURE_SSL_REDIRECT=False)
class PatientWorkspaceDocumentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = os.path.join(os.getcwd(), "test_media_uploads")
        os.makedirs(cls._temp_media, exist_ok=True)
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media, MEDIA_URL="/media/")
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user("docstaff", password="pass12345", is_staff=True)
        self.patient = Patient.objects.create(
            name="Patient Workspace",
            phone="09175550000",
            email="patientworkspace@test.com",
        )
        booking_date = timezone.localdate() + timedelta(days=1)
        Appointment.objects.create(
            patient=self.patient,
            name=self.patient.name,
            phone=self.patient.phone,
            email=self.patient.email,
            date=booking_date,
            start_time=time(10, 0),
            timeslot="10:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=["Consultation"],
        )

    def test_staff_can_open_patient_workspace(self):
        self.client.login(username="docstaff", password="pass12345")
        response = self.client.get(reverse("dashboard:patients"), {"patient": self.patient.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient Workspace")
        self.assertContains(response, self.patient.patient_code)

    def test_patient_queue_supports_sort_dropdown(self):
        self.client.login(username="docstaff", password="pass12345")
        older = Patient.objects.create(
            name="Older Patient",
            phone="09170000001",
            email="older@test.com",
        )
        newer = Patient.objects.create(
            name="Newest Patient",
            phone="09170000002",
            email="newer@test.com",
        )
        booking_date = timezone.localdate() + timedelta(days=2)
        Appointment.objects.create(
            patient=older,
            name=older.name,
            phone=older.phone,
            email=older.email,
            date=booking_date,
            start_time=time(9, 0),
            timeslot="9:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=["Consultation"],
        )
        Appointment.objects.create(
            patient=newer,
            name=newer.name,
            phone=newer.phone,
            email=newer.email,
            date=booking_date,
            start_time=time(11, 0),
            timeslot="11:00 AM",
            status=Appointment.STATUS_CONFIRMED,
            services=["Consultation"],
        )

        response = self.client.get(reverse("dashboard:patients"), {"sort": "oldest"})

        self.assertEqual(response.status_code, 200)
        queue_names = [patient.name for patient in response.context["patient_queue"]]
        self.assertEqual(queue_names[0], "Patient Workspace")
        self.assertEqual(queue_names[1], "Older Patient")
        self.assertEqual(queue_names[2], "Newest Patient")
        self.assertContains(response, 'option value="oldest" selected')

    def test_staff_can_upload_patient_document(self):
        self.client.login(username="docstaff", password="pass12345")
        uploaded = SimpleUploadedFile(
            "agreement.pdf",
            b"fake agreement content",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("dashboard:patients"),
            {
                "document_action": "upload_document",
                "patient_id": str(self.patient.id),
                "doc-title": "Signed agreement",
                "doc-document_type": PatientDocument.TYPE_AGREEMENT,
                "doc-file": uploaded,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PatientDocument.objects.filter(
                patient=self.patient,
                title="Signed agreement",
                document_type=PatientDocument.TYPE_AGREEMENT,
            ).exists()
        )

@override_settings(WEATHERAPI_KEY="", SECURE_SSL_REDIRECT=False)
class WebsiteManagementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            "webstaff",
            password="pass12345",
            is_staff=True,
        )
        self.content = SiteContent.objects.create(
            hero_title="Original Hero",
            hero_subtitle="Original subtitle",
            hero_cta_text="Book Now",
            about_summary="Original about summary",
            contact_phone="09170000000",
            contact_email="original@test.com",
            clinic_address="Original address",
            hours_line_1_label="Mon-Fri",
            hours_line_1_value="9:00am - 5:00pm",
            hours_line_2_label="Sat",
            hours_line_2_value="Closed",
            service_1_title="Service One",
            service_1_summary="Service one summary",
            service_2_title="Service Two",
            service_2_summary="Service two summary",
            service_3_title="Service Three",
            service_3_summary="Service three summary",
        )

    def test_staff_can_open_website_management_page(self):
        self.client.login(username="webstaff", password="pass12345")
        response = self.client.get(reverse("dashboard:website"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Website Management")
        self.assertIn("form", response.context)

    def test_staff_can_update_website_content(self):
        self.client.login(username="webstaff", password="pass12345")

        response = self.client.post(
            reverse("dashboard:website"),
            {
                "hero_title": "Updated Hero",
                "hero_subtitle": "Updated subtitle",
                "hero_cta_text": "Schedule Today",
                "about_summary": "Updated about summary",
                "contact_phone": "09171112222",
                "contact_email": "updated@test.com",
                "clinic_address": "Updated clinic address",
                "hours_line_1_label": "Mon-Wed",
                "hours_line_1_value": "8:00am - 4:00pm",
                "hours_line_2_label": "Thu-Sat",
                "hours_line_2_value": "10:00am - 6:00pm",
                "service_1_title": "Updated Service 1",
                "service_1_summary": "Updated service 1 summary",
                "service_2_title": "Updated Service 2",
                "service_2_summary": "Updated service 2 summary",
                "service_3_title": "Updated Service 3",
                "service_3_summary": "Updated service 3 summary",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.content.refresh_from_db()
        self.assertEqual(self.content.hero_title, "Updated Hero")
        self.assertEqual(self.content.contact_email, "updated@test.com")
        self.assertEqual(self.content.service_3_title, "Updated Service 3")
        self.assertEqual(
            response.redirect_chain,
            [(f"{reverse('dashboard:website')}?saved=1", 302)],
        )
