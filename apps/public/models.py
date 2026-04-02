from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .richtext import normalize_rich_text

class SiteContent(models.Model):
    hero_title = models.CharField(max_length=140, default="We're Here for You. Dentistry That Understands.")
    hero_subtitle = models.TextField(
        blank=True,
        default="Say goodbye to anxiety. We focus on gentle, compassionate care tailored to your comfort level, making every step - from cleaning to advanced procedure - as easy as possible.",
    )
    hero_cta_text = models.CharField(max_length=80, default="Book an Appointment")
    hero_slide_1_background = models.ImageField(
        upload_to="site/heroes/",
        blank=True,
        null=True,
    )
    hero_slide_2_title = models.CharField(max_length=180, blank=True)
    hero_slide_2_subtitle = models.TextField(blank=True)
    hero_slide_2_cta_text = models.CharField(max_length=80, blank=True)
    hero_slide_2_background = models.ImageField(
        upload_to="site/heroes/",
        blank=True,
        null=True,
    )
    home_intro_heading = models.CharField(max_length=180, blank=True)
    home_intro_text = models.TextField(blank=True)
    home_intro_background = models.ImageField(
        upload_to="site/home/",
        blank=True,
        null=True,
    )
    
    home_services_kicker = models.CharField(max_length=120, blank=True)
    home_services_heading = models.CharField(max_length=180, blank=True)
    home_services_intro = models.TextField(blank=True)

    home_doctor_kicker = models.CharField(max_length=120, blank=True)
    home_doctor_heading = models.CharField(max_length=180, blank=True)
    home_doctor_intro = models.TextField(blank=True)

    about_kicker = models.CharField(max_length=120, blank=True)
    about_heading = models.CharField(max_length=180, blank=True)
    about_summary = models.TextField(blank=True)
    about_side_image = models.ImageField(
        upload_to="site/about/",
        blank=True,
        null=True,
    )
    about_founder_name = models.CharField(max_length=120, blank=True)
    about_founder_title = models.CharField(max_length=120, blank=True)
    about_founder_photo = models.ImageField(
        upload_to="site/founders/",
        blank=True,
        null=True,
    )
    page_banner_background = models.ImageField(
        upload_to="site/banners/",
        blank=True,
        null=True,
    )
    services_page_title = models.CharField(max_length=180, blank=True)
    contact_page_title = models.CharField(max_length=180, blank=True)
    contact_form_heading = models.CharField(max_length=180, blank=True)
    clinic_website_url = models.URLField(blank=True)
    clinic_landmarks = models.TextField(blank=True)

    contact_phone = models.CharField(max_length=40, blank=True)
    contact_email = models.EmailField(blank=True)
    clinic_address = models.TextField(blank=True)
    hours_line_1_label = models.CharField(max_length=120, blank=True)
    hours_line_1_value = models.CharField(max_length=120, blank=True)
    hours_line_2_label = models.CharField(max_length=120, blank=True)
    hours_line_2_value = models.CharField(max_length=120, blank=True)

    service_1_title = models.CharField(max_length=120, blank=True)
    service_1_summary = models.TextField(blank=True)
    service_1_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_2_title = models.CharField(max_length=120, blank=True)
    service_2_summary = models.TextField(blank=True)
    service_2_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_3_title = models.CharField(max_length=120, blank=True)
    service_3_summary = models.TextField(blank=True)
    service_3_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_4_title = models.CharField(max_length=120, blank=True)
    service_4_summary = models.TextField(blank=True)
    service_4_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_5_title = models.CharField(max_length=120, blank=True)
    service_5_summary = models.TextField(blank=True)
    service_5_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_6_title = models.CharField(max_length=120, blank=True)
    service_6_summary = models.TextField(blank=True)
    service_6_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_7_title = models.CharField(max_length=120, blank=True)
    service_7_summary = models.TextField(blank=True)
    service_7_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    service_8_title = models.CharField(max_length=120, blank=True)
    service_8_summary = models.TextField(blank=True)
    service_8_image = models.ImageField(upload_to="site/services/", blank=True, null=True)

    doctor_name = models.CharField(max_length=120, blank=True)
    doctor_title = models.CharField(max_length=120, blank=True)
    doctor_bio = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Content"
        verbose_name_plural = "Site Content"

    def __str__(self):
        return "Website Content"


class Testimonial(models.Model):
    patient_name = models.CharField(max_length=120)
    visit_label = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    photo = models.ImageField(upload_to="site/testimonials/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.patient_name


class BlogPost(models.Model):
    class Category(models.TextChoices):
        PREVENTIVE_CARE = "preventive-care", "Preventive Care"
        PEDIATRIC_DENTISTRY = "pediatric-dentistry", "Pediatric Dentistry"
        ORTHODONTICS = "orthodontics", "Orthodontics"
        RESTORATIVE_DENTISTRY = "restorative-dentistry", "Restorative Dentistry"
        CLINIC_UPDATES = "clinic-updates", "Clinic Updates"

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.CLINIC_UPDATES,
    )
    excerpt = models.TextField()
    body = models.TextField()
    image = models.ImageField(upload_to="site/blog/", blank=True, null=True)
    author_name = models.CharField(max_length=120, blank=True, default="Clinic Team")
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-id")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    @property
    def rendered_body(self):
        return normalize_rich_text(self.body)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "blog-post"
            slug = base_slug
            counter = 2
            while BlogPost.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
