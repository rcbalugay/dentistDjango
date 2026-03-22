from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render
from apps.staff.services.dashboard import get_cached_weather, get_latest_appointments
from django.utils import timezone
from apps.staff.services.chart_utils import build_appointment_chart
from apps.appointments.models import Appointment
from .auth import staff_only

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
    return render(request, "staff/index.html", ctx)

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