from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .constants import (
    CLINIC_HOLIDAYS,
    CLINIC_OPEN_WEEKDAYS,
    CLINIC_SLOT_TIMES,
    SAME_DAY_BOOKING_CUTOFF_HOURS,
)
from apps.appointments.models import Appointment
from apps.public.views import get_site_content, get_clinic_settings
from .forms import AppointmentForm

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

def appointment_form(request):
    success_dialog = request.session.pop("appointment_success_dialog", None)
    error_dialog = None

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            from django.db import IntegrityError
            try:
                appointment = form.save(status=Appointment.STATUS_PENDING)
                request.session["appointment_success_dialog"] = {
                    "appointment_code": appointment.appointment_code,
                    "tracking_url": f"{reverse('appointment_status')}?code={appointment.appointment_code}",
                }
                return redirect(f"{reverse('appointment_form')}#appointment-form-section")
            except IntegrityError:
                form.add_error(None, "The selected date or time is already booked by another user. Please choose a different date or time.")
                form.unavailable_reason = "booked"
                form.unavailable_date = form.cleaned_data.get("appointment_date")
                form.unavailable_time = form.cleaned_data.get("appointment_time")
                error_dialog = build_appointment_error_dialog(form)
        else:
            error_dialog = build_appointment_error_dialog(form)
    else:
        form = AppointmentForm()

    return render(request, "appointments/pages/appointment.html", {
        "form": form,
        "clinic_schedule": clinic_schedule_for_js(),
        "success_dialog": success_dialog,
        "error_dialog": error_dialog,
        "site_content": get_site_content,
        "settings": get_clinic_settings(),
    })


def appointment_status(request):
    lookup_code = (request.GET.get("code") or "").strip().upper()
    appointment = None
    lookup_error = ""

    if lookup_code:
        appointment = Appointment.objects.filter(appointment_code__iexact=lookup_code).first()
        if appointment is None:
            lookup_error = "No appointment was found for that appointment ID."

    return render(request, "appointments/pages/appointment_status.html", {
        "lookup_code": lookup_code,
        "appointment": appointment,
        "lookup_error": lookup_error,
        "site_content": get_site_content,
        "settings": get_clinic_settings(),
    })


from django.http import JsonResponse

def check_appointment_slot(request):
    date_str = request.GET.get("date")
    start_time_str = request.GET.get("start_time")

    if not date_str or not start_time_str:
        return JsonResponse({"available": False, "error": "Missing parameters"}, status=400)

    try:
        date_obj = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"available": False, "error": "Invalid date format"}, status=400)

    time_obj = None
    for fmt in ["%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S"]:
        try:
            time_obj = datetime.strptime(start_time_str.strip(), fmt).time()
            break
        except ValueError:
            pass

    if not time_obj:
        return JsonResponse({"available": False, "error": "Invalid time format"}, status=400)

    exists = Appointment.objects.filter(
        date=date_obj,
        start_time=time_obj,
        status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
    ).exists()

    return JsonResponse({"available": not exists})


