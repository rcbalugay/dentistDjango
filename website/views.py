from django.shortcuts import render
from django.core.mail import send_mail
from datetime import datetime

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

		return render(request, 'contact.html', {'message_name': message_name})

	else:
		return render(request, 'contact.html', {})

def about(request):
	return render(request, 'about.html', {})

def blog(request):
	return render(request, 'blog.html', {})

def department(request):
	return render(request, 'department.html', {})

def doctor(request):
	return render(request, 'doctor.html', {})

def appointment(request):
	if request.method == "POST":
		your_name = request.POST['your-name']
		your_phone = request.POST['your-phone']
		your_email = request.POST['your-email']
		your_date = request.POST['your-date']
		your_time = request.POST['your-time']

		# Format date from MM/DD/YYYY to 'Month DD, YYYY'
		try:
			parsed_date = datetime.strptime(your_date, "%m/%d/%Y")
			formatted_date = parsed_date.strftime("%A, %B %d, %Y")  # October 18, 2025
		except ValueError:
			formatted_date = your_date

		# Sending email
		appointment = "Name: " + your_name + " Phone: " + your_phone + " Email: " + your_email + " Date: " + your_date + " Time: " + your_time
		
		send_mail(
			'Appointment Request', # subject
			appointment, # message
			your_email, # from email
			['karasuscho1@gmail.com'], # to email
			)

		return render(request, 'appointment.html', {
			'your_name': your_name,
			'your_phone': your_phone,
			'your_email': your_email,
			'your_date': formatted_date,
			'your_time': your_time
		})

	else:
		return render(request, 'home.html', {})