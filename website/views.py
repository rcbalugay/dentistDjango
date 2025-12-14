from django.shortcuts import render, redirect
from django.core.mail import send_mail
from datetime import datetime
from .models import Appointment
from django.contrib import messages
from .constants import APPOINTMENT_SERVICES
from .forms import AppointmentForm

def home(request):
	return render(request, 'home.html', {})

def contact(request):
	if request.method == "POST":
		message_name = request.POST.get("name") 
		message_email = request.POST.get("email")
		message_subject = request.POST.get("subject")
		message = request.POST.get("message")

		# Sending email
		send_mail(
			message_subject, # subject
			message, # message
			message_email, # from email
			['karasuscho1@gmail.com'], # to email
			)

		return render(request, 'pages/contact.html', {'message_name': message_name})

	else:
		return render(request, 'pages/contact.html', {})

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