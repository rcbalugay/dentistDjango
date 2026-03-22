import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render

from .forms import ContactForm

logger = logging.getLogger(__name__)

def home(request):
    return render(request, "public/home.html")

def about(request):
    return render(request, "public/pages/about.html")

def blog(request):
    return render(request, "public/pages/blog.html")

def services(request):
    return render(request, "public/pages/services.html")

def doctor(request):
    return render(request, "public/pages/doctor.html", {})

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

    return render(request, "public/pages/contact.html", {"form": form})