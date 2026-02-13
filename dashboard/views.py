import ipaddress
import requests as http_requests
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max
from website.models import Appointment, Patient
from .utils.time_utils import (
    parse_timeslot, 
    format_html_time_to_timeslot,
    parse_date,
)
from .utils.chart_utils import build_appointment_chart
from website.constants import APPOINTMENT_SERVICES
from website.forms import AppointmentForm

# Create your views here.
def staff_only(user):
    return user.is_authenticated and user.is_staff

def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

def ip_for_query(ip: str) -> str:
    """Return a safe query value for WeatherAPI: real IP or 'auto:ip' for local/private."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            return "auto:ip"
        return ip
    except Exception:
        return "auto:ip"

def weather_by_ip(ip: str):
    """
    Return {'temp_c','city','country'} via WeatherAPI, or None on failure.
    """
    try:
        q = ip_for_query(ip)
        r = http_requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": settings.WEATHERAPI_KEY, "q": q, "aqi": "no"},
            timeout=5,
        )
        j = r.json()
        # Uncomment to see responses in console
        # print("WX DEBUG:", {"ip": ip, "q": q, "status": r.status_code, "resp": j})
        if "current" in j and "location" in j:
            return {
                "temp_c": round(j["current"]["temp_c"]),
                "city": j["location"]["name"],
                "country": j["location"]["country"],
            }
        return None
    except Exception as e:
        # print("WX ERROR:", e)
        return None

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
    wx = weather_by_ip(client_ip(request)) if settings.WEATHERAPI_KEY else None

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
    todays_slots = Appointment.objects.filter(date=today).order_by("timeslot", "name")

    # upcoming appointments list (next 7 days, sorted by real time)
    upcoming_qs = (
        Appointment.objects
        .filter(
            status__in=[
                Appointment.STATUS_CONFIRMED,
                Appointment.STATUS_COMPLETED,
            ]
        )
        .order_by("date")
    )

    # sort in Python by (date, parsed timeslot)
    upcoming = sorted(
        upcoming_qs,
        key=lambda a: (a.date, parse_timeslot(a.timeslot or ""))
    )

    # latest patients (based on most recently completed appointments)
    completed_qs = (
    Appointment.objects
    .filter(status=Appointment.STATUS_COMPLETED)
    .order_by("-date", "-start_time", "-id")
    )

    latest_patients = []
    seen = set()

    for a in completed_qs:
        # Use contact identity to avoid showing the same person repeatedly
        key = (
            (a.phone or "").strip(),
            (a.email or "").strip(),
            (a.name or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        latest_patients.append(a)
        if len(latest_patients) == 5:
            break

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
        appoint_id = request.POST.get("appointment_id")
        action = request.POST.get("action")
        appoint = get_object_or_404(Appointment, id=appoint_id)

        if action == "approve":
            appoint.status = Appointment.STATUS_CONFIRMED
            appoint.save()
        elif action == "cancel":
            appoint.status = Appointment.STATUS_CANCELLED
            appoint.save()
        elif action == "complete":
            appoint.status = Appointment.STATUS_COMPLETED
            appoint.save()
        # "reschedule" can later redirect to an edit form if you add one

        return redirect("dashboard:appointments")

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
	return render(request, 'dashboard/pages/patients.html', {
        "active_page": "patients",
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

