from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from datetime import datetime
from .models import Appointment
from django.contrib import messages
from django.conf import settings
from .constants import APPOINTMENT_SERVICES
from .forms import AppointmentForm, ContactForm
import logging

logger = logging.getLogger(__name__)

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
            return redirect('appointment_form')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForm()
    
    # Use this to limit services on landing page
    # landing_services = APPOINTMENT_SERVICES[:4]
    return render(request, "pages/appointment.html", {
        "form": form, # replace this with landing_service if needed
    })