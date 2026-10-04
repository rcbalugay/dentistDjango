import os
import shutil
from datetime import time, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.patients.models import Patient, PatientDocument
from apps.staff.permissions import (
    ROLE_ADMINISTRATOR,
    ROLE_DENTIST,
    ROLE_RECEPTIONIST,
    is_administrator,
    is_dentist,
    is_receptionist,
    is_active_staff,
    can_view_patient_documents,
    can_upload_patient_documents,
    can_delete_patient_documents,
    can_manage_content,
)
from apps.staff.services.role_service import assign_staff_role, setup_roles_and_permissions

User = get_user_model()


@override_settings(WEATHERAPI_KEY="", SECURE_SSL_REDIRECT=False)
class StaffPermissionHelperTests(TestCase):
    def setUp(self):
        setup_roles_and_permissions()
        self.anon = AnonymousUser()
        self.regular_user = User.objects.create_user("regular", password="pwd", is_staff=False)
        self.staff_no_role = User.objects.create_user("staff_no_role", password="pwd", is_staff=True)
        self.inactive_staff = User.objects.create_user("inactive_staff", password="pwd", is_staff=True, is_active=False)

        self.receptionist = User.objects.create_user("receptionist", password="pwd", is_staff=True)
        assign_staff_role(self.receptionist, ROLE_RECEPTIONIST)

        self.dentist = User.objects.create_user("dentist", password="pwd", is_staff=True)
        assign_staff_role(self.dentist, ROLE_DENTIST)

        self.admin = User.objects.create_user("admin_staff", password="pwd", is_staff=True)
        assign_staff_role(self.admin, ROLE_ADMINISTRATOR)

        self.superuser = User.objects.create_superuser("superuser", password="pwd")

    def test_anonymous_and_non_staff_helpers(self):
        for user in [self.anon, self.regular_user, self.staff_no_role, self.inactive_staff]:
            self.assertFalse(is_administrator(user))
            self.assertFalse(is_dentist(user))
            self.assertFalse(is_receptionist(user))
            self.assertFalse(is_active_staff(user))
            self.assertFalse(can_view_patient_documents(user))
            self.assertFalse(can_upload_patient_documents(user))
            self.assertFalse(can_delete_patient_documents(user))
            self.assertFalse(can_manage_content(user))

    def test_receptionist_helpers(self):
        self.assertTrue(is_active_staff(self.receptionist))
        self.assertTrue(is_receptionist(self.receptionist))
        self.assertFalse(is_dentist(self.receptionist))
        self.assertFalse(is_administrator(self.receptionist))
        self.assertFalse(can_view_patient_documents(self.receptionist))
        self.assertFalse(can_upload_patient_documents(self.receptionist))
        self.assertFalse(can_delete_patient_documents(self.receptionist))
        self.assertFalse(can_manage_content(self.receptionist))

    def test_dentist_helpers(self):
        self.assertTrue(is_active_staff(self.dentist))
        self.assertTrue(is_dentist(self.dentist))
        self.assertFalse(is_receptionist(self.dentist))
        self.assertFalse(is_administrator(self.dentist))
        self.assertTrue(can_view_patient_documents(self.dentist))
        self.assertTrue(can_upload_patient_documents(self.dentist))
        self.assertFalse(can_delete_patient_documents(self.dentist))
        self.assertFalse(can_manage_content(self.dentist))

    def test_administrator_and_superuser_helpers(self):
        for user in [self.admin, self.superuser]:
            self.assertTrue(is_active_staff(user))
            self.assertTrue(is_administrator(user))
            self.assertTrue(is_dentist(user))
            self.assertTrue(is_receptionist(user))
            self.assertTrue(can_view_patient_documents(user))
            self.assertTrue(can_upload_patient_documents(user))
            self.assertTrue(can_delete_patient_documents(user))
            self.assertTrue(can_manage_content(user))

    def test_assign_staff_role_mutual_exclusivity(self):
        user = User.objects.create_user("switch_user", password="pwd", is_staff=True)
        assign_staff_role(user, ROLE_DENTIST)
        self.assertEqual(user.groups.count(), 1)
        self.assertEqual(user.groups.first().name, ROLE_DENTIST)

        assign_staff_role(user, ROLE_RECEPTIONIST)
        self.assertEqual(user.groups.count(), 1)
        self.assertEqual(user.groups.first().name, ROLE_RECEPTIONIST)


@override_settings(WEATHERAPI_KEY="", SECURE_SSL_REDIRECT=False)
class StaffRoleViewBoundaryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = os.path.join(os.getcwd(), "test_media_m7")
        os.makedirs(cls._temp_media, exist_ok=True)
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media, MEDIA_URL="/media/")
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        setup_roles_and_permissions()
        self.patient = Patient.objects.create(name="M7 Patient", phone="09170000099", email="m7@test.com")
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
        self.doc = PatientDocument.objects.create(
            patient=self.patient,
            title="Private Record",
            document_type=PatientDocument.TYPE_AGREEMENT,
            file=SimpleUploadedFile("record.pdf", b"encrypted doc content", content_type="application/pdf"),
        )

        self.receptionist = User.objects.create_user("m7_rec", password="pwd", is_staff=True)
        assign_staff_role(self.receptionist, ROLE_RECEPTIONIST)

        self.dentist = User.objects.create_user("m7_dentist", password="pwd", is_staff=True)
        assign_staff_role(self.dentist, ROLE_DENTIST)

        self.admin = User.objects.create_user("m7_admin", password="pwd", is_staff=True)
        assign_staff_role(self.admin, ROLE_ADMINISTRATOR)

        self.staff_no_role = User.objects.create_user("m7_no_role", password="pwd", is_staff=True)

    # --- Django Admin Lockdown Tests ---
    def test_receptionist_cannot_access_django_admin(self):
        self.client.login(username="m7_rec", password="pwd")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 403)

    def test_dentist_cannot_access_django_admin(self):
        self.client.login(username="m7_dentist", password="pwd")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 403)

    def test_staff_without_role_cannot_access_django_admin(self):
        self.client.login(username="m7_no_role", password="pwd")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_access_django_admin(self):
        self.client.login(username="m7_admin", password="pwd")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_django_admin(self):
        superuser = User.objects.create_superuser("m7_super", password="pwd")
        self.client.login(username="m7_super", password="pwd")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

    # --- Dashboard Access & Boundaries Tests ---
    def test_anonymous_redirected_to_login(self):
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:appointments"),
            reverse("dashboard:patients"),
            reverse("dashboard:inquiries"),
            reverse("dashboard:website"),
            reverse("dashboard:settings"),
            reverse("dashboard:download_patient_document", args=[self.doc.id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("dashboard:login"), response.url)

    def test_staff_without_role_forbidden(self):
        self.client.login(username="m7_no_role", password="pwd")
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:appointments"),
            reverse("dashboard:patients"),
            reverse("dashboard:inquiries"),
            reverse("dashboard:website"),
            reverse("dashboard:settings"),
            reverse("dashboard:download_patient_document", args=[self.doc.id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_receptionist_allowed_endpoints(self):
        self.client.login(username="m7_rec", password="pwd")
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:appointments")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:appointments_chart")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:inquiries")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:message")).status_code, 302)

        # Patients GET allowed, but document list is empty!
        response = self.client.get(reverse("dashboard:patients"), {"patient": self.patient.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["document_items"], [])
        self.assertIsNone(response.context["insurance_document"])

    def test_receptionist_forbidden_endpoints(self):
        self.client.login(username="m7_rec", password="pwd")
        # Cannot download documents
        self.assertEqual(
            self.client.get(reverse("dashboard:download_patient_document", args=[self.doc.id])).status_code,
            403,
        )
        # Cannot upload documents
        upload_resp = self.client.post(
            reverse("dashboard:patients"),
            {
                "document_action": "upload_document",
                "patient_id": str(self.patient.id),
                "doc-title": "Unauthorized Upload",
                "doc-document_type": PatientDocument.TYPE_AGREEMENT,
                "doc-file": SimpleUploadedFile("test.pdf", b"data", content_type="application/pdf"),
            },
        )
        self.assertEqual(upload_resp.status_code, 403)

        # Cannot access website content or clinic settings
        self.assertEqual(self.client.get(reverse("dashboard:website")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:settings")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:blog")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:services")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:team")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:testimonials")).status_code, 403)

    def test_dentist_allowed_endpoints(self):
        self.client.login(username="m7_dentist", password="pwd")
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:appointments")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:appointments_chart")).status_code, 200)

        # Patients GET has full document list
        response = self.client.get(reverse("dashboard:patients"), {"patient": self.patient.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["document_items"]), 1)

        # Dentist can download documents
        self.assertEqual(
            self.client.get(reverse("dashboard:download_patient_document", args=[self.doc.id])).status_code,
            200,
        )

        # Dentist can upload documents
        upload_resp = self.client.post(
            reverse("dashboard:patients"),
            {
                "document_action": "upload_document",
                "patient_id": str(self.patient.id),
                "doc-title": "Dentist Upload",
                "doc-document_type": PatientDocument.TYPE_AGREEMENT,
                "doc-file": SimpleUploadedFile("dentist_file.pdf", b"data", content_type="application/pdf"),
            },
        )
        self.assertEqual(upload_resp.status_code, 302)

    def test_dentist_forbidden_endpoints(self):
        self.client.login(username="m7_dentist", password="pwd")
        self.assertEqual(self.client.get(reverse("dashboard:inquiries")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:message")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:website")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:settings")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:blog")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:services")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:team_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:testimonials")).status_code, 403)

    def test_administrator_has_full_access(self):
        self.client.login(username="m7_admin", password="pwd")
        urls = [
            reverse("dashboard:home"),
            reverse("dashboard:appointments"),
            reverse("dashboard:appointments_chart"),
            reverse("dashboard:patients"),
            reverse("dashboard:inquiries"),
            reverse("dashboard:website"),
            reverse("dashboard:settings"),
            reverse("dashboard:blog"),
            reverse("dashboard:services"),
            reverse("dashboard:team_create"),
            reverse("dashboard:testimonials"),
            reverse("dashboard:download_patient_document", args=[self.doc.id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Admin failed on {url}")
