from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.contrib import messages
from django.conf import settings
from .constants import CLINIC_OPEN_WEEKDAYS, CLINIC_SLOT_TIMES
from .models import Appointment
from .forms import AppointmentForm, ContactForm
import logging

logger = logging.getLogger(__name__)

def clinic_schedule_for_js():
    return {
        "open_weekdays_js": sorted((day + 1) % 7 for day in CLINIC_OPEN_WEEKDAYS),
        "slot_labels": [slot.strftime("%I:%M %p").lstrip("0") for slot in CLINIC_SLOT_TIMES],
    }

def home(request):
    return render(request, 'home.html', {})

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

    return render(request, "pages/contact.html", {"form": form})


def about(request):
    return render(request, 'pages/about.html', {})

def blog(request):
    return render(request, 'pages/blog.html', {})

def services(request):
    return render(request, 'pages/services.html', {})

def doctor(request):
    return render(request, 'pages/doctor.html', {})

def appointment_form(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            form.save(status=Appointment.STATUS_PENDING)
            messages.success(request, "Your appointment request has been sent. We will contact you to confirm.")
            return redirect("appointment_form")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForm()

    return render(request, "pages/appointment.html", {
        "form": form,
        "clinic_schedule": clinic_schedule_for_js(),
    })