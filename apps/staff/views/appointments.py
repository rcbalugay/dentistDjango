from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.staff.services.time_utils import parse_date
from apps.appointments.forms import StaffAppointmentForm

from .auth import staff_only

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def appointments(request):
    q = request.GET.get("q", "").strip()
    today = timezone.localdate()

    # ---- Handle actions from buttons (Approve / Cancel / Complete etc.) ----
    if request.method == "POST":
        next_url = request.META.get("HTTP_REFERER") or redirect("dashboard:appointments").url
        appoint_id = request.POST.get("appointment_id")
        action = request.POST.get("action")

        # Guard: only allow known actions
        allowed_actions = {"approve", "cancel", "complete"}
        if action not in allowed_actions:
            messages.error(request, "Invalid action.")
            return redirect(next_url)

        appoint = get_object_or_404(Appointment, id=appoint_id)

        # Guard: check if the action is valid for the current status
        if action == "approve" and appoint.status != Appointment.STATUS_PENDING:
            messages.error(request, "Only pending appointments can be approved.")
            return redirect(next_url)

        if action == "complete" and appoint.status != Appointment.STATUS_CONFIRMED:
            messages.error(request, "Only confirmed appointments can be completed.")
            return redirect(next_url)

        if action == "cancel" and appoint.status not in [Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]:
            messages.error(request, "Only pending/confirmed appointments can be cancelled.")
            return redirect(next_url)

        # Performs the action
        if action == "approve":
            appoint.status = Appointment.STATUS_CONFIRMED
        elif action == "cancel":
            appoint.status = Appointment.STATUS_CANCELLED
        elif action == "complete":
            appoint.status = Appointment.STATUS_COMPLETED
        # "reschedule" can later redirect to an edit form if you add one

        appoint.save(update_fields=["status"])
        return redirect(next_url)

    # ---- Base queryset with search filter ----
    base_qs = Appointment.objects.all()

    if q:
        base_qs = base_qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
        )

    # Requests = pending appointments
    pending_requests = (
        base_qs.filter(status=Appointment.STATUS_PENDING)
        .order_by("date", "start_time", "name")
    )

    # Upcoming confirmed appointments (today and future)
    upcoming_appointments = (
        base_qs.filter(
            status=Appointment.STATUS_CONFIRMED,
            date__gte=today,
        )
        .order_by("date", "start_time", "name")
    )

    status_filter = request.GET.get("history_status", "").strip()
    start_str = request.GET.get("history_from", "").strip()
    end_str = request.GET.get("history_to", "").strip()

    # Recent cancelled / completed (history)
    recent_history_qs = base_qs.filter(
        status__in=[Appointment.STATUS_CANCELLED, Appointment.STATUS_COMPLETED]
    )

    VALID_HISTORY_STATUSES = [
        Appointment.STATUS_CANCELLED,
        Appointment.STATUS_COMPLETED,
    ]

    if status_filter in VALID_HISTORY_STATUSES:
        recent_history_qs = recent_history_qs.filter(status=status_filter)
    else:
        status_filter = ""  # reset to empty if invalid value provided

    start_date = parse_date(start_str)
    end_date = parse_date(end_str)

    if start_date: 
        recent_history_qs = recent_history_qs.filter(date__gte=start_date)
    if end_date:
        recent_history_qs = recent_history_qs.filter(date__lte=end_date)

    recent_history_qs = recent_history_qs.order_by("-date","start_time", "name")

    history_page_number = request.GET.get("history_page")
    history_paginator = Paginator(recent_history_qs, 5)
    recent_history = history_paginator.get_page(history_page_number)

    from urllib.parse import urlencode

    history_query = {
        "history_status": status_filter,
        "history_from": start_str,
        "history_to": end_str,
    }
    if q:
        history_query["q"] = q

    history_querystring = urlencode({k: v for k, v in history_query.items() if v})

    ctx = {
        "q": q,
        "pending_requests": pending_requests,
        "upcoming_appointments": upcoming_appointments,
        "recent_history": recent_history,
        "history_status": status_filter,
        "history_from": start_str,
        "history_to": end_str,
        "history_querystring": history_querystring,
        "active_page": "appointments",
    }
    return render(request, "staff/pages/dappointments.html", ctx)

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def appointments_form(request):
    if request.method == 'POST':
        form = StaffAppointmentForm(request.POST)
        if form.is_valid():
            form.save(status=Appointment.STATUS_CONFIRMED)
            messages.success(request, "Appointment has been created.")
            return redirect('dashboard:appointments')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StaffAppointmentForm()

    return render(request, 'staff/pages/appointmentform.html', {
        "active_page": "appointments",
        "form": form,
    })