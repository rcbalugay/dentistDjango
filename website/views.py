from django.shortcuts import render, redirect
from django.core.mail import send_mail
from datetime import datetime
from .models import Appointment
from django.contrib import messages

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

def appointment(request):
    if request.method == "POST":
        name     = request.POST.get("name", "").strip()
        phone    = request.POST.get("phone", "").strip()
        email    = request.POST.get("email", "").strip()
        services = request.POST.getlist("services") 
        date_str = request.POST.get("appointment_date", "") or request.POST.get("date", "")
        timeslot = request.POST.get("appointment_time", "") or request.POST.get("timeslot", "")

        # validation part
        if not (name and phone and date_str and timeslot and services):
            messages.error(request, "Please complete name, phone, date, time and services.")
            return redirect("appointment")

        try:
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("appointment")

        Appointment.objects.create(
            name=name, phone=phone, email=email,
            services=services, date=appt_date, timeslot=timeslot
        )

        messages.success(request, "Hello, an appointment has been request.")
        return redirect("appointment")

    return render(request, "pages/appointment.html", {})