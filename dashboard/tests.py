from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

# Create your tests here.
@override_settings(WEATHERAPI_KEY="")
class DashboardAccessSmokeTests(TestCase):
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