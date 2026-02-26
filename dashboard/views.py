from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Q, Count, Max, Min
from website.models import Appointment, Patient
from .utils.time_utils import (
    parse_timeslot, 
    format_html_time_to_timeslot,
    parse_date,
)
from .utils.chart_utils import build_appointment_chart
from .utils.weather import client_ip, ip_for_query, weather_by_ip
from website.constants import APPOINTMENT_SERVICES
from website.forms import AppointmentForm
from dashboard.services import get_cached_weather, get_latest_appointments

# Create your views here.
def staff_only(user):
    return user.is_authenticated and user.is_staff

class RememberMeLoginView(LoginView):
    template_name = "dashboard/pages/login.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        remember = self.request.POST.get("remember") == "on"
        # 2 weeks if checked; session-only if not
        self.request.session.set_expiry(1209600 if remember else 0)
        return resp

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def index(request):
    wx = get_cached_weather(request)
    # enable when needed, does the same as the line of code above this
    # if settings.WEATHERAPI_KEY:
    #     ip = client_ip(request)
    #     q = ip_for_query(ip)
    #     cache_key = f"weather_{ip}"
    #     wx = cache.get(cache_key)

    #     if wx is None:
    #         wx = weather_by_ip(ip)
    #         # cache even if None(?) maybe just cache valid results only
    #         if wx:
    #             cache.set(cache_key, wx, 300)

    # --- dates
    today = timezone.localdate()
    now = timezone.now()
    last_30 = now - timedelta(days=30)
    prev_30_start = now - timedelta(days=60)
    next_7 = today + timedelta(days=7)
    prev_7_start = today - timedelta(days=7)

    # --- Helper
    def pct_change(curr: int, prev: int) -> float:
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round((curr - prev) * 100.0 / prev, 2)

    # --- KPIs
    patients_today = Appointment.objects.filter(date=today).count()
    
    total_patients = (
        Appointment.objects
        .values("name", "phone", "email")
        .distinct()
        .count()
    )

    requests_30 = Appointment.objects.filter(created_at__gte=last_30).count()
    requests_prev30 = Appointment.objects.filter(created_at__gte=prev_30_start,
                                                 created_at__lt=last_30).count()
    requests_change = pct_change(requests_30, requests_prev30)

    upcoming_week = Appointment.objects.filter(date__gte=today, date__lte=next_7).count()
    prev_week = Appointment.objects.filter(date__lt=today, date__gte=prev_7_start).count()
    upcoming_change = pct_change(upcoming_week, prev_week)

    # existing data you already render
    todays_slots = (
        Appointment.objects
        .filter(date=today)
        .order_by("start_time", "name")
    )

    # upcoming appointments list
    upcoming = (
        Appointment.objects
        .filter(
            status__in=[
                Appointment.STATUS_CONFIRMED,
                Appointment.STATUS_COMPLETED,
            ]
        )
        .order_by("date", "start_time", "name")
    )

    # latest patients (based on most recently completed appointments)
    latest_patients = get_latest_appointments(limit=5)

    # --------------- APPOINTMENTS CHART (Day / Week / Month / Year) ---------------
    view_mode = (request.GET.get("ap_view") or "day").lower()
    start_param = request.GET.get("ap_start")
    if start_param:
        try:
            base = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            base = today
    else:
        base = today

    chart = build_appointment_chart(view_mode, base)

    appts_chart_labels = chart["labels"]
    appts_chart_values = chart["values"]

    # context
    ctx = {
        "weather": wx or {"temp_c": 21, "city": "Pampanga", "country": "Philippines"},
        "today": today,
        "todays_slots": todays_slots,

        # KPI values
        "kpi_patients_today": patients_today,
        "kpi_patients_today_change": requests_change,   # use 30-day trend label

        "kpi_total_patients": total_patients,
        "kpi_total_patients_change": requests_change,   # re-use same 30d trend (or compute your own)

        "kpi_requests_30": requests_30,
        "kpi_requests_change": requests_change,         # % vs previous 30 days

        "kpi_placeholder": upcoming_week,               # “upcoming this week”
        "kpi_placeholder_change": upcoming_change, 
        
        "appts_chart_labels": appts_chart_labels,
        "appts_chart_values": appts_chart_values,
        "appts_view": chart["view"],
        "appts_period_label": chart["period_label"],
        "appts_prev_start": chart["prev_start"],
        "appts_next_start": chart["next_start"], 

        # Patients
        "latest_patients": latest_patients,
        "upcoming": upcoming,
        "active_page": "home",
    }
    return render(request, "dashboard/index.html", ctx)

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def appointments_chart(request):
    today = timezone.localdate()

    view_mode = (request.GET.get("ap_view") or "day").lower()
    start_param = request.GET.get("ap_start")

    if start_param:
        try:
            base = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            base = today
    else:
        base = today

    chart = build_appointment_chart(view_mode, base)
    return JsonResponse(chart)

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
    return render(request, "dashboard/pages/dappointments.html", ctx)

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def patients(request):
    q = request.GET.get("q", "").strip()
    selected_key = request.GET.get("patient", "").strip()
    today = timezone.localdate()

    base_qs = Appointment.objects.all()
    if q:
        base_qs = base_qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
        )

    patient_queue = list(
        base_qs.values("name", "phone", "email")
        .annotate(
            patient_key=Min("id"),
            first_seen=Min("created_at"),
            last_seen=Max("date"),
            total_appointments=Count("id"),
            pending_count=Count("id", filter=Q(status=Appointment.STATUS_PENDING)),
            confirmed_count=Count("id", filter=Q(status=Appointment.STATUS_CONFIRMED)),
            completed_count=Count("id", filter=Q(status=Appointment.STATUS_COMPLETED)),
            cancelled_count=Count("id", filter=Q(status=Appointment.STATUS_CANCELLED)),
        )
        .order_by("-last_seen", "name")
    )

    selected_patient = None
    upcoming_schedule = []
    visit_history = []
    document_items = []
    quick_stats = {
        "total": 0,
        "completed": 0,
        "upcoming": 0,
        "cancelled": 0,
        "adherence": 0,
    }
    assurance_card = {
        "member_number": "",
        "status": "New",
        "expiry": today,
    }

    if patient_queue:
        selected_patient = patient_queue[0]
        if selected_key.isdigit():
            wanted = int(selected_key)
            selected_patient = next(
                (row for row in patient_queue if row["patient_key"] == wanted),
                selected_patient,
            )

        selected_appointments = (
            base_qs.filter(
                name=selected_patient["name"],
                phone=selected_patient["phone"],
                email=selected_patient["email"],
            )
            .order_by("-date", "-start_time")
        )

        upcoming_schedule = list(
            selected_appointments.filter(
                date__gte=today,
                status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
            )
            .order_by("date", "start_time")[:6]
        )
        visit_history = list(selected_appointments[:8])

        completed = selected_patient["completed_count"]
        total = selected_patient["total_appointments"]
        pending = selected_patient["pending_count"]
        confirmed = selected_patient["confirmed_count"]
        cancelled = selected_patient["cancelled_count"]

        adherence = round((completed * 100.0 / total), 1) if total else 0
        quick_stats = {
            "total": total,
            "completed": completed,
            "upcoming": pending + confirmed,
            "cancelled": cancelled,
            "adherence": adherence,
        }

        assurance_card = {
            "member_number": f"{selected_patient['patient_key']:03d}-{today.year}-{total:03d}",
            "status": "Active" if completed > 0 else "New",
            "expiry": today + timedelta(days=365),
        }

        for a in visit_history[:4]:
            services_label = ", ".join(a.services) if a.services else "General dental service"
            note_words = len((a.notes or "").split())
            document_items.append({
                "title": f"Visit summary #{a.id}",
                "subtitle": services_label,
                "meta": f"{a.date:%d %b %Y} - {note_words} note words",
                "status": a.get_status_display(),
            })

    return render(request, "dashboard/pages/patients.html", {
        "active_page": "patients",
        "q": q,
        "today": today,
        "patient_queue": patient_queue,
        "selected_patient": selected_patient,
        "upcoming_schedule": upcoming_schedule,
        "visit_history": visit_history,
        "document_items": document_items,
        "quick_stats": quick_stats,
        "assurance_card": assurance_card,
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def message(request):
	return render(request, 'dashboard/pages/message.html', {
        "active_page": "message",
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def blog(request):
	return render(request, 'dashboard/pages/blog.html', {
        "active_page": "blog",
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def profile(request):
	return render(request, 'dashboard/pages/profile.html', {
        "active_page": "profile",
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def appointments_form(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            form.save(status=Appointment.STATUS_PENDING)
            messages.success(request, "Appointment has been created.")
            return redirect('dashboard:appointments')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForm()
    
    return render(request, 'dashboard/pages/appointmentform.html', {
        "active_page": "appointments",
        "form": form,
    })

