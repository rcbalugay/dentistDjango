from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.public.models import BlogPost, SiteContent, Testimonial

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

    def test_priority_one_fields_render_on_public_pages(self):
        SiteContent.objects.create(
            pk=1,
            services_page_title="Managed Services Title",
            contact_page_title="Managed Contact Title",
            contact_form_heading="Managed Contact Heading",
            clinic_website_url="https://managed.example.com",
            clinic_landmarks="Managed landmark one, Managed landmark two",
        )

        services_response = self.client.get(reverse("services"))
        self.assertEqual(services_response.status_code, 200)
        self.assertContains(services_response, "Managed Services Title")

        contact_response = self.client.get(reverse("contact"))
        self.assertEqual(contact_response.status_code, 200)
        self.assertContains(contact_response, "Managed Contact Title")
        self.assertContains(contact_response, "Managed Contact Heading")
        self.assertContains(contact_response, "Managed landmark one, Managed landmark two")

    def test_about_page_shows_doctor_profile_content(self):
        SiteContent.objects.create(
            pk=1,
            doctor_name="Dr. Managed Dentist",
            doctor_title="General Dentistry",
            doctor_bio="Calm, gentle care with a prevention-first approach.",
        )

        response = self.client.get(reverse("about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meet the Dentist")
        self.assertContains(response, "Dr. Managed Dentist")
        self.assertContains(response, "General Dentistry")
        self.assertContains(response, "Calm, gentle care with a prevention-first approach.")

    def test_homepage_shows_testimonials_and_blog_sections(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient Stories")
        self.assertContains(response, "Helpful Reading Between Visits")

    def test_homepage_uses_published_testimonials_and_blog_posts(self):
        Testimonial.objects.create(
            patient_name="Published Patient",
            visit_label="Consultation",
            quote="Published testimonial quote.",
            sort_order=0,
            is_published=True,
        )
        Testimonial.objects.create(
            patient_name="Hidden Patient",
            visit_label="Consultation",
            quote="Hidden testimonial quote.",
            sort_order=91,
            is_published=False,
        )
        published_post = BlogPost.objects.create(
            title="Published Post",
            excerpt="Published excerpt.",
            body="Published body.",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=True,
        )
        BlogPost.objects.create(
            title="Draft Post",
            excerpt="Draft excerpt.",
            body="Draft body.",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=False,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Patient")
        self.assertNotContains(response, "Hidden Patient")
        self.assertContains(response, "Published Post")
        self.assertNotContains(response, "Draft Post")
        self.assertContains(response, published_post.get_absolute_url())

    def test_blog_list_and_detail_show_only_published_posts(self):
        published_post = BlogPost.objects.create(
            title="Visible Blog Entry",
            category=BlogPost.Category.CLINIC_UPDATES,
            excerpt="Visible excerpt.",
            body="Visible body.",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=True,
        )
        draft_post = BlogPost.objects.create(
            title="Hidden Blog Entry",
            category=BlogPost.Category.PREVENTIVE_CARE,
            excerpt="Hidden excerpt.",
            body="Hidden body.",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=False,
        )

        list_response = self.client.get(reverse("blog"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Visible Blog Entry")
        self.assertNotContains(list_response, "Hidden Blog Entry")

        detail_response = self.client.get(reverse("blog_detail", args=[published_post.slug]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Visible body.")
        self.assertContains(detail_response, "Clinic Updates")

        hidden_response = self.client.get(reverse("blog_detail", args=[draft_post.slug]))
        self.assertEqual(hidden_response.status_code, 404)

    def test_blog_list_can_filter_by_category_and_renders_rich_text(self):
        orthodontic_post = BlogPost.objects.create(
            title="Braces Planning",
            category=BlogPost.Category.ORTHODONTICS,
            excerpt="Orthodontic excerpt.",
            body="<h2>Heading</h2><p>Detailed <strong>guidance</strong>.</p>",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=True,
        )
        BlogPost.objects.create(
            title="Cleaning Advice",
            category=BlogPost.Category.PREVENTIVE_CARE,
            excerpt="Preventive excerpt.",
            body="<p>Cleaning copy.</p>",
            author_name="Clinic Team",
            published_at=timezone.now(),
            is_published=True,
        )

        list_response = self.client.get(reverse("blog"), {"category": BlogPost.Category.ORTHODONTICS})
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Braces Planning")
        self.assertNotContains(list_response, "Cleaning Advice")

        detail_response = self.client.get(reverse("blog_detail", args=[orthodontic_post.slug]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "<strong>guidance</strong>", html=False)


