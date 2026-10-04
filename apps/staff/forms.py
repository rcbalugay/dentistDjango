from django import forms
from django.utils import timezone
from django.utils.text import slugify

from apps.public.models import BlogPost, SiteContent, Testimonial, ClinicSettings, Service, TeamMember
from apps.public.richtext import normalize_rich_text


class HomepageForm(forms.ModelForm):
    class Meta:
        model = SiteContent
        fields = [
            "hero_title",
            "hero_subtitle",
            "hero_cta_text",
            "hero_slide_1_background",
            "hero_slide_2_title",
            "hero_slide_2_subtitle",
            "hero_slide_2_cta_text",
            "hero_slide_2_background",
            "home_intro_heading",
            "home_intro_text",
            "home_intro_background",
            "home_services_kicker",
            "home_services_heading",
            "home_services_intro",
            "home_doctor_kicker",
            "home_doctor_heading",
            "home_doctor_intro",
            "doctor_name",
            "doctor_title",
            "doctor_bio",
            "meta_description",
            "meta_keywords",
        ]
        widgets = {
            "meta_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter home page meta description (recommended: 150-160 characters)..."
            }),
            "meta_keywords": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "dental, Porac dentist, pediatric dentistry..."
            }),
            "hero_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "We're Here for You. Gentle & Compassionate Care."
            }),
            "hero_subtitle": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Write a warm, welcoming description explaining your clinic's philosophy, patient comfort, and values..."
            }),
            "hero_cta_text": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Book an Appointment"
            }),
            "hero_slide_1_background": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "hero_slide_2_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Smile with Confidence (Complementary Slide 2 Headline)"
            }),
            "hero_slide_2_subtitle": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Highlight another key service, dental philosophy, or welcoming message..."
            }),
            "hero_slide_2_cta_text": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Meet Our Doctors"
            }),
            "hero_slide_2_background": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "home_intro_heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Modern Dentistry, Compassionate Care"
            }),
            "home_intro_text": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Provide a brief introductory description about your clinic's philosophy and services..."
            }),
            "home_intro_background": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "home_services_kicker": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "OUR SERVICES"
            }),
            "home_services_heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Comprehensive Dental Care for Everyone"
            }),
            "home_services_intro": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Learn more about the full range of preventive, cosmetic, and restorative dental procedures available at our clinic..."
            }),
            "home_doctor_kicker": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "MEET OUR TEAM"
            }),
            "home_doctor_heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your Health & Comfort is Our First Priority"
            }),
            "home_doctor_intro": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Get to know our skilled clinical staff and specialized dental health professionals..."
            }),
            "doctor_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Dr. Jane Doe"
            }),
            "doctor_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Lead Surgeon & Pediatric Dentist"
            }),
            "doctor_bio": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Summarize the featured doctor's medical background, certifications, and care philosophy..."
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field, "max_length") and field.max_length is not None:
                field.widget.attrs["maxlength"] = str(field.max_length)


class AboutForm(forms.ModelForm):
    class Meta:
        model = SiteContent
        fields = [
            "about_kicker",
            "about_heading",
            "about_summary",
            "about_side_image",
            "about_founder_name",
            "about_founder_title",
            "about_founder_photo",
            "page_banner_background",
            "services_page_title",
            "contact_page_title",
            "contact_form_heading",
        ]
        widgets = {
            "about_kicker": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "GET TO KNOW US"
            }),
            "about_heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Excellence in Dental Care Since [Year]"
            }),
            "about_summary": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Tell your clinic's history, founding story, core clinic mission, and dedication to oral hygiene..."
            }),
            "about_side_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "about_founder_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Dr. John Smith"
            }),
            "about_founder_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Clinic Founder & Senior Partner"
            }),
            "about_founder_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "page_banner_background": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "services_page_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Our Services & Treatments"
            }),
            "contact_page_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Get in Touch"
            }),
            "contact_form_heading": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Send a Message"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field, "max_length") and field.max_length is not None:
                field.widget.attrs["maxlength"] = str(field.max_length)

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = [
            "patient_name",
            "visit_label",
            "quote",
            "photo",
            "sort_order",
            "is_published",
        ]
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control"}),
            "visit_label": forms.TextInput(attrs={"class": "form-control"}),
            "quote": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BlogPostForm(forms.ModelForm):
    slug = forms.SlugField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    published_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"class": "form-control", "type": "datetime-local"},
        ),
    )

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "slug",
            "category",
            "excerpt",
            "body",
            "image",
            "author_name",
            "published_at",
            "is_published",
            "meta_description",
            "meta_keywords",
        ]
        widgets = {
            "meta_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter blog post meta description (recommended: 150-160 characters)..."
            }),
            "meta_keywords": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "oral health, dental tips, kids dental care..."
            }),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "excerpt": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "author_name": forms.TextInput(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.published_at:
            self.initial["published_at"] = timezone.localtime(self.instance.published_at).strftime("%Y-%m-%dT%H:%M")
        elif not self.initial.get("published_at"):
            self.initial["published_at"] = timezone.localtime(timezone.now()).strftime("%Y-%m-%dT%H:%M")

    def clean_slug(self):
        slug = slugify(self.cleaned_data.get("slug", ""))
        return slug

    def clean_body(self):
        return normalize_rich_text(self.cleaned_data.get("body", ""))

class ClinicSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSettings
        fields = "__all__"
        widgets = {
            "clinic_name": forms.TextInput(attrs={"class": "form-control"}),
            "clinic_website_url": forms.URLInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "clinic_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "clinic_landmarks": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "hours_line_1_label": forms.TextInput(attrs={"class": "form-control"}),
            "hours_line_1_value": forms.TextInput(attrs={"class": "form-control"}),
            "hours_line_2_label": forms.TextInput(attrs={"class": "form-control"}),
            "hours_line_2_value": forms.TextInput(attrs={"class": "form-control"}),
        }

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["title", "summary", "image", "sort_order", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "summary": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMember
        fields = ["name", "role", "bio", "photo", "sort_order", "is_published"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Dr. Jane Smith"}),
            "role": forms.TextInput(attrs={"class": "form-control", "placeholder": "Orthodontist / Oral Surgeon"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Provide a brief medical bio and care philosophy..."}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if hasattr(field, "max_length") and field.max_length is not None:
                field.widget.attrs["maxlength"] = str(field.max_length)

