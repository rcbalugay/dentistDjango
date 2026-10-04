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


    doctor_name = models.CharField(max_length=120, blank=True)
    doctor_title = models.CharField(max_length=120, blank=True)
    doctor_bio = models.TextField(blank=True)

    meta_description = models.TextField(blank=True, help_text="Highly recommended for Google results (150-160 characters).")
    meta_keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated SEO keywords.")

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
    meta_description = models.TextField(blank=True, help_text="Configure custom dynamic snippet for search engine indexing.")
    meta_keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords for this post.")
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

class ClinicSettings(models.Model):
    clinic_name = models.CharField(max_length=120, default="Our Clinic")
    clinic_website_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    clinic_address = models.TextField(blank=True)
    clinic_landmarks = models.TextField(blank=True)
    hours_line_1_label = models.CharField(max_length=120, blank=True, default="Monday - Friday")
    hours_line_1_value = models.CharField(max_length=120, blank=True, default="8:00 AM - 5:00 PM")
    hours_line_2_label = models.CharField(max_length=120, blank=True, default="Saturday")
    hours_line_2_value = models.CharField(max_length=120, blank=True, default="9:00 AM - 1:00 PM")

    class Meta:
        verbose_name = "Clinic Settings"
        verbose_name_plural = "Clinic Settings"

    def __str__(self):
        return "Clinic Settings"

    @property
    def opening_hours_spec(self):
        import re
        from datetime import datetime
        
        specs = []
        days_map = {
            "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
            "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
        }
        ordered_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        
        def parse_days(label):
            normalized = label.lower().replace("&", ",").replace("and", ",")
            segments = [s.strip() for s in normalized.split(",") if s.strip()]
            
            found_days = []
            for segment in segments:
                range_match = re.search(r"(\w+)\s*[-–to]+\s*(\w+)", segment)
                if range_match:
                    start_day_raw = range_match.group(1)[:3]
                    end_day_raw = range_match.group(2)[:3]
                    
                    def normalize_day(d):
                        if d.startswith("thu"): return "thu"
                        if d.startswith("tue"): return "tue"
                        return d
                        
                    start_day = normalize_day(start_day_raw)
                    end_day = normalize_day(end_day_raw)
                    
                    try:
                        start_idx = ordered_days.index(start_day)
                        end_idx = ordered_days.index(end_day)
                        if start_idx <= end_idx:
                            selected = ordered_days[start_idx:end_idx+1]
                        else:
                            selected = ordered_days[start_idx:] + ordered_days[:end_idx+1]
                        for d in selected:
                            if days_map[d] not in found_days:
                                found_days.append(days_map[d])
                    except ValueError:
                        pass
                else:
                    for short, full in days_map.items():
                        if segment.startswith(short) or (short == "thu" and segment.startswith("thu")) or (short == "tue" and segment.startswith("tue")):
                            if full not in found_days:
                                found_days.append(full)
                                break
            return found_days
            
        def parse_times(val):
            if "closed" in val.lower():
                return None, None
                
            matches = re.findall(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", val.lower())
            if len(matches) >= 2:
                times = []
                for t in matches[:2]:
                    t_str = t.strip().upper()
                    if "AM" in t_str or "PM" in t_str:
                        if ":" not in t_str:
                            t_str = re.sub(r"(\d+)\s*(AM|PM)", r"\1:00 \2", t_str)
                        try:
                            dt = datetime.strptime(t_str, "%I:%M %p")
                            times.append(dt.strftime("%H:%M"))
                        except ValueError:
                            pass
                    else:
                        try:
                            dt = datetime.strptime(t_str, "%H:%M")
                            times.append(dt.strftime("%H:%M"))
                        except ValueError:
                            try:
                                dt = datetime.strptime(t_str, "%H")
                                times.append(dt.strftime("%H:%M"))
                            except ValueError:
                                pass
                if len(times) == 2:
                    return times[0], times[1]
            return None, None

        # Process Line 1
        if self.hours_line_1_label and self.hours_line_1_value:
            days = parse_days(self.hours_line_1_label)
            opens, closes = parse_times(self.hours_line_1_value)
            if days and opens and closes:
                specs.append({
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": days,
                    "opens": opens,
                    "closes": closes
                })
                
        # Process Line 2
        if self.hours_line_2_label and self.hours_line_2_value:
            days = parse_days(self.hours_line_2_label)
            opens, closes = parse_times(self.hours_line_2_value)
            if days and opens and closes:
                specs.append({
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": days,
                    "opens": opens,
                    "closes": closes
                })
                
        return specs

    @property
    def opening_hours_spec_json(self):
        import json
        return json.dumps(self.opening_hours_spec)



class Service(models.Model):
    title = models.CharField(max_length=120)
    summary = models.TextField(blank=True)
    image = models.ImageField(upload_to="site/services/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title


class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, help_text="e.g. Pediatric Dentist, Orthodontist, Clinic Manager")
    bio = models.TextField(blank=True, help_text="Short bio displayed on card highlights.")
    photo = models.ImageField(upload_to="site/team/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"{self.name} - {self.role}"

