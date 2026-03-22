from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse


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
