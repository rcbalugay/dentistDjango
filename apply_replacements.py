import os

BASE_DIR = r"c:\dentistsite\dentist\apps\public"

# 1. Update views.py
views_path = os.path.join(BASE_DIR, "views.py")
with open(views_path, "r", encoding="utf-8") as f:
    views_content = f.read()

views_content = views_content.replace(
    "from .models import BlogPost, SiteContent, Testimonial",
    "from .models import BlogPost, SiteContent, Testimonial, Service, ClinicSettings"
)

if "def get_clinic_settings():" not in views_content:
    settings_func = """
def get_clinic_settings():
    settings_obj, _ = ClinicSettings.objects.get_or_create(pk=1)
    return settings_obj
"""
    views_content = views_content.replace("def get_site_content():", settings_func + "\ndef get_site_content():")

# We want to add "clinic_settings": get_clinic_settings() and "services": Service.objects.filter(is_published=True).order_by("sort_order") to context dicts
views_content = views_content.replace(
    '{"site_content": get_site_content()}', 
    '{"site_content": get_site_content(), "settings": get_clinic_settings(), "services": Service.objects.filter(is_published=True).order_by("sort_order")}'
)
views_content = views_content.replace(
    '"site_content": get_site_content(),\n',
    '"site_content": get_site_content(),\n            "settings": get_clinic_settings(),\n            "services": Service.objects.filter(is_published=True).order_by("sort_order"),\n'
)

with open(views_path, "w", encoding="utf-8") as f:
    f.write(views_content)


# 2. Update Templates
replacements = {
    "site_content.contact_phone": "settings.contact_phone",
    "site_content.clinic_address": "settings.clinic_address",
    "site_content.hours_line_1_label": "settings.hours_line_1_label",
    "site_content.hours_line_1_value": "settings.hours_line_1_value",
    "site_content.hours_line_2_label": "settings.hours_line_2_label",
    "site_content.hours_line_2_value": "settings.hours_line_2_value",
    "site_content.clinic_landmarks": "settings.clinic_landmarks",
    "site_content.contact_email": "settings.contact_email",
    "site_content.contact_page_title": "settings.contact_page_title",
    "site_content.contact_form_heading": "settings.contact_form_heading",
    "site_content.clinic_website_url": "settings.clinic_website_url",
}

def replace_in_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements.items():
        content = content.replace(old, new)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

replace_in_file(os.path.join(BASE_DIR, "templates", "public", "base.html"))
replace_in_file(os.path.join(BASE_DIR, "templates", "public", "pages", "contact.html"))
