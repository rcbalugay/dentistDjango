from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .constants import (
    CLINIC_HOLIDAYS,
    CLINIC_OPEN_WEEKDAYS,
    CLINIC_SLOT_TIMES,
    SAME_DAY_BOOKING_CUTOFF_HOURS,
)
from .models import Appointment
from .forms import AppointmentForm, ContactForm
import logging

logger = logging.getLogger(__name__)

def clinic_schedule_for_js():
    return {
        "open_weekdays_js": sorted((day + 1) % 7 for day in CLINIC_OPEN_WEEKDAYS),
        "slot_labels": [slot.strftime("%I:%M %p").lstrip("0") for slot in CLINIC_SLOT_TIMES],
    }


def get_next_available_slots(start_dt, limit=3, search_days=21):
    tz = timezone.get_current_timezone()
    now_cutoff = timezone.now() + timedelta(hours=SAME_DAY_BOOKING_CUTOFF_HOURS)
    earliest_dt = max(start_dt, now_cutoff)
    start_date = earliest_dt.date()
    end_date = start_date + timedelta(days=search_days)

    booked_slots = set(
        Appointment.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
        ).values_list("date", "start_time")
    )

    suggestions = []
    for offset in range(search_days + 1):
        candidate_date = start_date + timedelta(days=offset)

        if candidate_date.weekday() not in CLINIC_OPEN_WEEKDAYS:
            continue
        if candidate_date in CLINIC_HOLIDAYS:
            continue

        for slot_time in CLINIC_SLOT_TIMES:
            candidate_dt = timezone.make_aware(
                datetime.combine(candidate_date, slot_time),
                tz,
            )
            if candidate_dt < earliest_dt:
                continue
            if (candidate_date, slot_time) in booked_slots:
                continue

            suggestions.append({
                "date_iso": candidate_date.isoformat(),
                "time_value": slot_time.strftime("%I:%M %p").lstrip("0"),
                "date_label": candidate_date.strftime("%B %d, %Y"),
                "time_label": slot_time.strftime("%I:%M %p").lstrip("0"),
            })
            if len(suggestions) >= limit:
                return suggestions

    return suggestions


def build_appointment_error_dialog(form):
    reason = getattr(form, "unavailable_reason", "")
    requested_date = getattr(form, "unavailable_date", None)
    requested_time = getattr(form, "unavailable_time", None)

    if not reason or not requested_date or not requested_time:
        return None

    tz = timezone.get_current_timezone()
    requested_dt = timezone.make_aware(
        datetime.combine(requested_date, requested_time),
        tz,
    )

    if reason == "booked":
        return {
            "title": "Time Slot Unavailable",
            "subtitle": "This appointment slot is already booked.",
            "detail_title": "Requested Time Unavailable",
            "requested_date": requested_date.strftime("%B %d, %Y"),
            "requested_time": requested_time.strftime("%I:%M %p").lstrip("0"),
            "tip": "Popular time slots fill up quickly. Select an available slot below or choose a different date when booking.",
            "suggestions": get_next_available_slots(requested_dt + timedelta(minutes=1)),
        }

    if reason == "too_late":
        return {
            "title": "Time Slot Unavailable",
            "subtitle": f"Appointments must be booked at least {SAME_DAY_BOOKING_CUTOFF_HOURS} hours in advance.",
            "detail_title": "Requested Time Too Soon",
            "requested_date": requested_date.strftime("%B %d, %Y"),
            "requested_time": requested_time.strftime("%I:%M %p").lstrip("0"),
            "tip": "Please choose a later time slot so we have enough lead time to prepare your visit.",
            "suggestions": get_next_available_slots(requested_dt),
        }

    return None

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
    success_dialog = request.session.pop("appointment_success_dialog", None)
    error_dialog = None

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(status=Appointment.STATUS_PENDING)
            request.session["appointment_success_dialog"] = {
                "appointment_code": appointment.appointment_code,
                "tracking_url": f"{reverse('appointment_status')}?code={appointment.appointment_code}",
            }
            return redirect(f"{reverse('appointment_form')}#appointment-form-section")
        else:
            error_dialog = build_appointment_error_dialog(form)
    else:
        form = AppointmentForm()

    return render(request, "pages/appointment.html", {
        "form": form,
        "clinic_schedule": clinic_schedule_for_js(),
        "success_dialog": success_dialog,
        "error_dialog": error_dialog,
    })


def appointment_status(request):
    lookup_code = (request.GET.get("code") or "").strip().upper()
    appointment = None
    lookup_error = ""

    if lookup_code:
        appointment = Appointment.objects.filter(appointment_code__iexact=lookup_code).first()
        if appointment is None:
            lookup_error = "No appointment was found for that appointment ID."

    return render(request, "pages/appointment_status.html", {
        "lookup_code": lookup_code,
        "appointment": appointment,
        "lookup_error": lookup_error,
    })
