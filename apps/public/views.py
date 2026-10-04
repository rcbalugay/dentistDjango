import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ContactForm
from .models import BlogPost, SiteContent, Testimonial, Service, ClinicSettings, TeamMember

logger = logging.getLogger(__name__)



def get_clinic_settings():
    settings_obj, _ = ClinicSettings.objects.get_or_create(pk=1)
    
    fallback_defaults = {
        "clinic_address": "Purok 1 Planas Bridge, Porac, Pampanga 2008",
        "contact_phone": "(+63) 967 406 4184",
        "contact_email": "clinic@example.com",
        "hours_line_1_label": "Mon & Wed, Sat - Sun:",
        "hours_line_1_value": "9:00am - 6:00pm",
        "hours_line_2_label": "Tues & Thurs - Fri:",
        "hours_line_2_value": "Closed",
        "clinic_landmarks": "Nathaniel's Water Station, Planas Tricycle Terminal Station, Gasoline Station"
    }
    
    updated = False
    for field_name, value in fallback_defaults.items():
        if not getattr(settings_obj, field_name):
            setattr(settings_obj, field_name, value)
            updated = True
            
    if updated:
        settings_obj.save()
        
    return settings_obj

def get_site_content():
    content, _ = SiteContent.objects.get_or_create(
        pk=1,
        defaults={
            "hero_title": "We're Here for You. Dentistry That Understands.",
            "hero_subtitle": "Say goodbye to anxiety. We focus on gentle, compassionate care tailored to your comfort level, making every step - from cleaning to advanced procedure - as easy as possible.",
            "hero_cta_text": "Make an Appointment",
            "hero_slide_2_title": "Your Confident Smile Starts Here",
            "hero_slide_2_subtitle": (
                "Unlock your true potential with comprehensive, cutting-edge cosmetic "
                "dental care. Schedule your consultation today to design the lasting "
                "impression you deserve."
            ),
            "hero_slide_2_cta_text": "Make an Appointment",
            "home_intro_heading": "We promised to take care our patients and we delivered.",
            "home_intro_text": (
                "A small river named Duden flows by their place and supplies it with "
                "the necessary regelialia. It is a paradisematic country."
            ),
            "home_services_kicker": "Services",
            "home_services_heading": "Our Clinic Services",
            "home_services_intro": "We offer a range of dental services to help you achieve your best smile.",
            "home_doctor_kicker": "Our Staff Team",
            "home_doctor_heading": "Meet the Person Behind Your Smile",
            "home_doctor_intro": "Discover the dedicated clinician who will personally oversee your care at every visit.",
            "about_summary": (
                "A small river named Duden flows by their place and supplies it with the "
                "necessary regelialia. It is a paradisematic country, in which roasted "
                "parts of sentences fly into your mouth. Even the all-powerful Pointing "
                "has no control about the blind texts it is an almost unorthographic "
                "life One day however a small line of blind text by the name of Lorem "
                "Ipsum decided to leave for the far World of Grammar."
            ),
            "about_kicker": "Welcome to Dentista",
            "about_heading": "Medical specialty concerned with the care of acutely ill hospitalized patients",
            "services_page_title": "Our Treatments & Services",
            "contact_page_title": "Contact Us",
            "contact_form_heading": "Send Us a Message",
            "clinic_website_url": "",
            "clinic_landmarks": "Nathaniel's Water Station, Planas Tricycle Terminal Station, Gasoline Station",
            "about_founder_name": "Dr. Paul Foster",
            "about_founder_title": "CEO, Founder",
            "doctor_name": "Dr. Gennie Lyn Perez, DMD",
            "doctor_title": "General & Pediatric Dentistry",
            "doctor_bio": (
                "Gentle, prevention-focused care with special interest in minimally "
                "invasive dentistry. Member, Philippine Dental Association."
            ),
        },
    )

    updated = False

    if content.hero_title == "We're Here for You. <span>Dentistry That Understands.</span>":
        content.hero_title = "We're Here for You. Dentistry That Understands."
        updated = True

    if "Ã¢â‚¬â€" in content.hero_subtitle:
        content.hero_subtitle = content.hero_subtitle.replace("Ã¢â‚¬â€", "-")
        updated = True

    fallback_defaults = {
        "services_page_title": "Our Treatments & Services",
        "contact_page_title": "Contact Us",
        "contact_form_heading": "Send Us a Message",
        "clinic_landmarks": "Nathaniel's Water Station, Planas Tricycle Terminal Station, Gasoline Station",
    }

    for field_name, value in fallback_defaults.items():
        if not getattr(content, field_name):
            setattr(content, field_name, value)
            updated = True

    if updated:
        content.save()

    return content


def get_published_testimonials():
    return Testimonial.objects.filter(is_published=True)


def get_published_blog_posts():
    return BlogPost.objects.filter(is_published=True, published_at__lte=timezone.now())


def get_published_team_members():
    return TeamMember.objects.filter(is_published=True).order_by("sort_order", "id")


def home(request):
    return render(
        request,
        "public/home.html",
        {
            "site_content": get_site_content(),
            "settings": get_clinic_settings(),
            "services": Service.objects.filter(is_published=True).order_by("sort_order"),
            "testimonials": get_published_testimonials()[:4],
            "featured_posts": get_published_blog_posts()[:3],
            "team_members": get_published_team_members(),
        },
    )



def about(request):
    return render(
        request,
        "public/pages/about.html",
        {
            "site_content": get_site_content(),
            "settings": get_clinic_settings(),
            "services": Service.objects.filter(is_published=True).order_by("sort_order"),
            "team_members": get_published_team_members(),
        },
    )


def blog(request):
    blog_posts = get_published_blog_posts()
    active_category = request.GET.get("category", "").strip()
    valid_categories = {value for value, _ in BlogPost.Category.choices}

    if active_category in valid_categories:
        blog_posts = blog_posts.filter(category=active_category)
    else:
        active_category = ""

    return render(
        request,
        "public/pages/blog.html",
        {
            "site_content": get_site_content(),
            "settings": get_clinic_settings(),
            "services": Service.objects.filter(is_published=True).order_by("sort_order"),
            "blog_posts": blog_posts,
            "blog_categories": BlogPost.Category.choices,
            "active_blog_category": active_category,
        },
    )


def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        is_published=True,
        published_at__lte=timezone.now(),
    )
    return render(
        request,
        "public/pages/blog_detail.html",
        {
            "site_content": get_site_content(),
            "settings": get_clinic_settings(),
            "services": Service.objects.filter(is_published=True).order_by("sort_order"),
            "post": post,
            "recent_posts": get_published_blog_posts().exclude(pk=post.pk)[:3],
        },
    )


def services(request):
    return render(request, "public/pages/services.html", {"site_content": get_site_content(), "settings": get_clinic_settings(), "services": Service.objects.filter(is_published=True).order_by("sort_order")})


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            body = (
                f"Name: {data['name']}\n"
                f"Email: {data['email']}\n\n"
                f"{data['message']}"
            )

            try:
                email = EmailMessage(
                    subject=data["subject"],
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[data["email"]],
                )
                email.send(fail_silently=False)
            except Exception:
                logger.exception("Contact form email send failed")
                messages.error(
                    request,
                    "We could not send your message right now. Please try again later.",
                )
            else:
                messages.success(request, "Your message has been sent.")
                return redirect("contact")
    else:
        form = ContactForm()

    return render(
        request,
        "public/pages/contact.html",
        {
            "form": form,
            "site_content": get_site_content(),
            "settings": get_clinic_settings(),
            "services": Service.objects.filter(is_published=True).order_by("sort_order"),
        },
    )

def sitemap_xml(request):
    host = request.build_absolute_uri('/')
    urls = []
    
    # Core static pages
    core_urls = [
        "",
        "about/",
        "services/",
        "blog/",
        "contact/",
        "appointment/",
    ]
    for rel_url in core_urls:
        urls.append(f"{host}{rel_url}")
        
    # Dynamic blog posts
    blog_qs = BlogPost.objects.filter(is_published=True, published_at__lte=timezone.now())
    for post in blog_qs:
        urls.append(f"{host}blog/{post.slug}/")
        
    # Render XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml_content += '  <url>\n'
        xml_content += f'    <loc>{url}</loc>\n'
        xml_content += '    <changefreq>daily</changefreq>\n'
        xml_content += '    <priority>0.80</priority>\n'
        xml_content += '  </url>\n'
    xml_content += '</urlset>'
    
    return HttpResponse(xml_content, content_type="application/xml")

def robots_txt(request):
    host = request.build_absolute_uri('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {host}sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")
