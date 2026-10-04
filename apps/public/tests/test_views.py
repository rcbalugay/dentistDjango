from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.public.models import BlogPost, SiteContent, Testimonial, Service, ClinicSettings, TeamMember

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
        )
        ClinicSettings.objects.create(
            pk=1,
            contact_phone="09175550000",
            contact_email="managed@test.com",
            clinic_address="Managed clinic address",
            hours_line_1_label="Mon-Fri",
            hours_line_1_value="9:00am - 5:00pm",
            hours_line_2_label="Sat",
            hours_line_2_value="Closed",
        )
        Service.objects.create(title="Managed Service 1", summary="Managed summary 1", is_published=True, sort_order=1)
        Service.objects.create(title="Managed Service 2", summary="Managed summary 2", is_published=True, sort_order=2)
        Service.objects.create(title="Managed Service 3", summary="Managed summary 3", is_published=True, sort_order=3)

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
        )
        ClinicSettings.objects.create(
            pk=1,
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

from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

class SEOAndImageEngineTests(TestCase):
    def test_sitemap_xml_serves_valid_sitemap_index(self):
        BlogPost.objects.create(
            title="Dynamic Article For Sitemap",
            category=BlogPost.Category.CLINIC_UPDATES,
            excerpt="Sitemap post excerpt.",
            body="Sitemap body content.",
            published_at=timezone.now(),
            is_published=True,
        )
        response = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertContains(response, "<urlset")
        self.assertContains(response, "/blog/dynamic-article-for-sitemap/")
        
    def test_robots_txt_serves_valid_sitemap_link(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "User-agent: *")
        self.assertContains(response, "Sitemap: http://testserver/sitemap.xml")
        
    def test_dynamic_seo_metadata_rendering(self):
        # Home page SEO metadata
        SiteContent.objects.create(
            pk=1,
            meta_description="Dynamic Dental Home Page Description.",
            meta_keywords="porac, dentist, teeth, pedodontist",
        )
        home_res = self.client.get(reverse("home"))
        self.assertEqual(home_res.status_code, 200)
        self.assertContains(home_res, '<meta name="description" content="Dynamic Dental Home Page Description.">')
        self.assertContains(home_res, '<meta name="keywords" content="porac, dentist, teeth, pedodontist">')
        self.assertContains(home_res, '<link rel="canonical" href="http://testserver/">')
        
        # Blog post SEO metadata
        post = BlogPost.objects.create(
            title="SEO Optimized Post",
            excerpt="Article excerpt.",
            body="Article body content.",
            meta_description="Custom Blog Article Meta Tag.",
            meta_keywords="kids dentistry, child toothcare",
            published_at=timezone.now(),
            is_published=True,
        )
        blog_res = self.client.get(reverse("blog_detail", args=[post.slug]))
        self.assertEqual(blog_res.status_code, 200)
        self.assertContains(blog_res, '<meta name="description" content="Custom Blog Article Meta Tag.">')
        self.assertContains(blog_res, '<meta name="keywords" content="kids dentistry, child toothcare">')
        self.assertContains(blog_res, '<link rel="canonical" href="http://testserver/blog/seo-optimized-post/">')

    def test_webp_image_compression_signal(self):
        # Create a mock heavy raw image (RGBA)
        f = BytesIO()
        image = Image.new("RGBA", (1400, 1400), (255, 0, 0, 255))
        image.save(f, "PNG")
        f.seek(0)
        uploaded_image = SimpleUploadedFile("raw_heavy_photo.png", f.read(), content_type="image/png")
        
        # Create a new dynamic service upload
        service = Service.objects.create(
            title="WebP Compressed Treatment",
            summary="This service has a compressed photo.",
            image=uploaded_image,
            is_published=True,
        )
        
        # Refresh from database and assert WebP formatting and scaling occurred
        service.refresh_from_db()
        self.assertTrue(service.image.name.endswith(".webp"))
        
        # Assert image dimensions were scaled successfully down below responsive threshold (800px)
        img = Image.open(service.image.file)
        self.assertEqual(img.format, "WEBP")
        self.assertLessEqual(img.width, 800)
        self.assertLessEqual(img.height, 800)

    def test_webp_image_compression_signal_for_team_member(self):
        # Create a mock heavy raw image (RGBA)
        f = BytesIO()
        image = Image.new("RGBA", (1000, 1000), (0, 255, 0, 255))
        image.save(f, "PNG")
        f.seek(0)
        uploaded_image = SimpleUploadedFile("team_raw_photo.png", f.read(), content_type="image/png")
        
        # Create a new dynamic team member upload
        member = TeamMember.objects.create(
            name="Dr. Jane Smith",
            role="Orthodontist",
            bio="Dynamic orthodontist bio details.",
            photo=uploaded_image,
            is_published=True,
        )
        
        # Refresh from database and assert WebP formatting and scaling occurred
        member.refresh_from_db()
        self.assertTrue(member.photo.name.endswith(".webp"))
        
        # Assert image dimensions were scaled successfully down below responsive threshold (600px)
        img = Image.open(member.photo.file)
        self.assertEqual(img.format, "WEBP")
        self.assertLessEqual(img.width, 600)
        self.assertLessEqual(img.height, 600)

    def test_homepage_shows_clinical_team_members(self):
        TeamMember.objects.create(
            name="Dr. Paul Foster",
            role="Founder & Chief Dentist",
            bio="Dynamic founder bio.",
            is_published=True,
            sort_order=1
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dr. Paul Foster")
        self.assertContains(response, "Founder &amp; Chief Dentist")



