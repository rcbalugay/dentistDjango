import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

from .forms import ContactForm
from .models import SiteContent

logger = logging.getLogger(__name__)


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
            "about_founder_name": "Dr. Paul Foster",
            "about_founder_title": "CEO, Founder",
            "contact_phone": "(+63) 967 406 4184",
            "contact_email": "clinic@example.com",
            "clinic_address": "Purok 1 Planas Bridge, Porac, Pampanga 2008",
            "hours_line_1_label": "Mon & Wed, Sat - Sun:",
            "hours_line_1_value": "9:00am - 6:00pm",
            "hours_line_2_label": "Tues & Thurs - Fri:",
            "hours_line_2_value": "Closed",
            "service_1_title": "General Dentistry",
            "service_1_summary": "Comprehensive oral exams, cleaning, and preventive dental care for all ages.",
            "service_2_title": "Pediatric Dentistry",
            "service_2_summary": "Gentle and fun dental care tailored for children to build lifelong oral habits.",
            "service_3_title": "Orthodontics",
            "service_3_summary": "Braces and aligner treatments to correct teeth alignment and improve smiles.",
            "service_4_title": "Teeth Whitening",
            "service_4_summary": "Brighten stained or discolored teeth with safe cosmetic whitening care.",
            "service_5_title": "Dental Calculus Removal",
            "service_5_summary": "Professional cleaning and scaling to remove tartar buildup and protect gum health.",
            "service_6_title": "Periodontics",
            "service_6_summary": "Treatment focused on gum health, periodontal care, and long-term oral stability.",
            "service_7_title": "Braces & Orthodontics",
            "service_7_summary": "Alignment solutions designed to improve bite, spacing, and smile confidence.",
            "service_8_title": "Root Canal",
            "service_8_summary": "Tooth-saving treatment that relieves pain and protects infected teeth.",
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

    if updated:
        content.save()

    return content


def home(request):
    return render(request, "public/home.html", {"site_content": get_site_content()})


def about(request):
    return render(request, "public/pages/about.html", {"site_content": get_site_content()})


def blog(request):
    return render(request, "public/pages/blog.html", {"site_content": get_site_content()})


def services(request):
    return render(request, "public/pages/services.html", {"site_content": get_site_content()})


def doctor(request):
    return render(request, "public/pages/doctor.html", {"site_content": get_site_content()})


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
        },
    )
