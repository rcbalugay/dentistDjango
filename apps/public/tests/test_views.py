from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.public.models import SiteContent

@override_settings(
    DEFAULT_FROM_EMAIL="clinic@test.com",
    CONTACT_EMAIL="owner@test.com",
)
class PublicPageSmokeTests(TestCase):
    def test_public_pages_load(self):
        urls = [
            reverse("home"),
            reverse("about"),
            reverse("services"),
            reverse("blog"),
            reverse("contact"),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    @patch("apps.public.views.EmailMessage.send", return_value=1)
    def test_contact_form_success_redirects_with_message(self, _send):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Inquiry",
                "message": "Hello from the smoke test.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Your message has been sent.", messages)

    def test_homepage_uses_site_content_values(self):
        SiteContent.objects.create(
            pk=1,
            hero_title="Managed Hero Title",
            hero_subtitle="Managed Hero Subtitle",
            hero_cta_text="Managed CTA",
            about_summary="Managed about summary",
            contact_phone="09175550000",
            contact_email="managed@test.com",
            clinic_address="Managed clinic address",
            hours_line_1_label="Mon-Fri",
            hours_line_1_value="9:00am - 5:00pm",
            hours_line_2_label="Sat",
            hours_line_2_value="Closed",
            service_1_title="Managed Service 1",
            service_1_summary="Managed summary 1",
            service_2_title="Managed Service 2",
            service_2_summary="Managed summary 2",
            service_3_title="Managed Service 3",
            service_3_summary="Managed summary 3",
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Managed Hero Title")
        self.assertContains(response, "Managed Hero Subtitle")
        self.assertContains(response, "Managed CTA")
        self.assertContains(response, "Managed Service 1")
        self.assertContains(response, "Managed Service 2")
        self.assertContains(response, "Managed Service 3")


