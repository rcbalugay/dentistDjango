import ipaddress
import requests as http_requests
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from datetime import date, timedelta, datetime, time
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from website.models import Appointment

# Create your views here.
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

@login_required
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
    def parse_timeslot(ts: str) -> time:
        """
        Convert timeslot text like '9:00 AM' or '10:30 AM' into a time object
        so we can sort correctly.
        """
        if not ts:
            return time(0, 0)
        for fmt in ("%I:%M %p", "%H:%M"):
            try:
                return datetime.strptime(ts, fmt).time()
            except ValueError:
                continue
        return time(0, 0)

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

    # latest patients (based on most recent appointments)
    latest_patients = (
        Appointment.objects
        .order_by("-created_at")[:5]
    )

    # --------------- APPOINTMENTS CHART (Day / Week / Month / Year) ---------------
    view_mode = (request.GET.get("ap_view") or "day").lower()
    if view_mode not in {"day", "week", "month", "year"}:
        view_mode = "day"

    start_param = request.GET.get("ap_start")
    if start_param:
        try:
            base = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            base = today
    else:
        base = today

    def add_months(d: date, n: int) -> date:
        """Return a date n months from d (always day=1)."""
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return date(y, m, 1)

    # ---------- DAY VIEW: last 7 days (or any 7-day window) ----------
    if view_mode == "day":
        window_days = 7
        period_end = base
        period_start = period_end - timedelta(days=window_days - 1)

        qs = (
            Appointment.objects
            .filter(date__range=(period_start, period_end))
            .values("date")
            .annotate(count=Count("id"))
        )
        counts_map = {row["date"]: row["count"] for row in qs}

        labels = []
        values = []
        for i in range(window_days):
            d = period_start + timedelta(days=i)
            labels.append(d.strftime("%d %b"))
            values.append(counts_map.get(d, 0))

        appts_period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b %Y')}"
        prev_start = (period_start - timedelta(days=window_days)).isoformat()
        next_start = (period_end + timedelta(days=window_days)).isoformat()

    # ---------- WEEK VIEW: 4 weekly buckets (W1..W4) ----------
    elif view_mode == "week":
        weeks_window = 4
        days_window = weeks_window * 7
        period_end = base
        period_start = period_end - timedelta(days=days_window - 1)

        qs = (
            Appointment.objects
            .filter(date__range=(period_start, period_end))
            .values("date")
        )

        week_counts = [0] * weeks_window
        for row in qs:
            d = row["date"]
            idx = (d - period_start).days // 7
            if 0 <= idx < weeks_window:
                week_counts[idx] += 1

        labels = [f"W{i+1}" for i in range(weeks_window)]
        values = week_counts

        appts_period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b %Y')}"
        prev_start = (period_start - timedelta(days=days_window)).isoformat()
        next_start = (period_end + timedelta(days=days_window)).isoformat()

    # ---------- MONTH VIEW: up to 6 months, aggregated per month ----------
    elif view_mode == "month":
        months_window = 6
        last_month_start = base.replace(day=1)
        first_month_start = add_months(last_month_start, -(months_window - 1))

        month_starts = [add_months(first_month_start, i) for i in range(months_window)]
        last_month_end = add_months(last_month_start, 1) - timedelta(days=1)

        qs = (
            Appointment.objects
            .filter(date__range=(first_month_start, last_month_end))
            .values("date")
        )

        month_counts = [0] * months_window
        for row in qs:
            d = row["date"]
            idx = (d.year - first_month_start.year) * 12 + (d.month - first_month_start.month)
            if 0 <= idx < months_window:
                month_counts[idx] += 1

        labels = [m.strftime("%b") for m in month_starts]
        values = month_counts

        appts_period_label = f"{first_month_start.strftime('%b %Y')} – {last_month_start.strftime('%b %Y')}"
        prev_start = add_months(last_month_start, -months_window).isoformat()
        next_start = add_months(last_month_start, months_window).isoformat()

    # ---------- YEAR VIEW: last 6 years, aggregated per year ----------
    else:  # view_mode == "year"
        years_window = 6
        last_year = base.year
        first_year = last_year - (years_window - 1)

        qs = (
            Appointment.objects
            .filter(date__year__gte=first_year, date__year__lte=last_year)
            .values("date__year")
            .annotate(count=Count("id"))
        )
        counts_map = {row["date__year"]: row["count"] for row in qs}

        labels = []
        values = []
        for y in range(first_year, last_year + 1):
            labels.append(str(y))
            values.append(counts_map.get(y, 0))

        appts_period_label = f"{first_year} – {last_year}"
        prev_start = date(first_year - years_window, 1, 1).isoformat()
        next_start = date(last_year + years_window, 1, 1).isoformat()

    appts_chart_labels = labels
    appts_chart_values = values

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
        "appts_view": view_mode,
        "appts_period_label": appts_period_label,
        "appts_prev_start": prev_start,
        "appts_next_start": next_start, 

        # Patients
        "latest_patients": latest_patients,
        "upcoming": upcoming,
        "active_page": "home",
    }
    return render(request, "dashboard/index.html", ctx)

@login_required
def appointments_chart(request):
    today = timezone.localdate()

    view_mode = (request.GET.get("ap_view") or "day").lower()
    if view_mode not in {"day", "week", "month", "year"}:
        view_mode = "day"

    start_param = request.GET.get("ap_start")
    if start_param:
        try:
            base = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError:
            base = today
    else:
        base = today

    def add_months(d: date, n: int) -> date:
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return date(y, m, 1)

    # ---------- DAY VIEW: last 7 days ----------
    if view_mode == "day":
        window_days = 7
        period_end = base
        period_start = period_end - timedelta(days=window_days - 1)

        qs = (
            Appointment.objects
            .filter(date__range=(period_start, period_end))
            .values("date")
            .annotate(count=Count("id"))
        )
        counts_map = {row["date"]: row["count"] for row in qs}

        labels = []
        values = []
        for i in range(window_days):
            d = period_start + timedelta(days=i)
            labels.append(d.strftime("%d %b"))
            values.append(counts_map.get(d, 0))

        period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b %Y')}"
        prev_start = (period_start - timedelta(days=window_days)).isoformat()
        next_start = (period_end + timedelta(days=window_days)).isoformat()

    # ---------- WEEK VIEW: 4 weekly buckets W1..W4 ----------
    elif view_mode == "week":
        weeks_window = 4
        days_window = weeks_window * 7
        period_end = base
        period_start = period_end - timedelta(days=days_window - 1)

        qs = (
            Appointment.objects
            .filter(date__range=(period_start, period_end))
            .values("date")
        )

        week_counts = [0] * weeks_window
        for row in qs:
            d = row["date"]
            idx = (d - period_start).days // 7
            if 0 <= idx < weeks_window:
                week_counts[idx] += 1

        labels = [f"W{i+1}" for i in range(weeks_window)]
        values = week_counts

        period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b %Y')}"
        prev_start = (period_start - timedelta(days=days_window)).isoformat()
        next_start = (period_end + timedelta(days=days_window)).isoformat()

    # ---------- MONTH VIEW: max 6 months, aggregated per month ----------
    elif view_mode == "month":
        months_window = 6
        last_month_start = base.replace(day=1)
        first_month_start = add_months(last_month_start, -(months_window - 1))

        month_starts = [add_months(first_month_start, i) for i in range(months_window)]
        last_month_end = add_months(last_month_start, 1) - timedelta(days=1)

        qs = (
            Appointment.objects
            .filter(date__range=(first_month_start, last_month_end))
            .values("date")
        )

        month_counts = [0] * months_window
        for row in qs:
            d = row["date"]
            idx = (d.year - first_month_start.year) * 12 + (d.month - first_month_start.month)
            if 0 <= idx < months_window:
                month_counts[idx] += 1

        labels = [m.strftime("%b") for m in month_starts]
        values = month_counts

        period_label = f"{first_month_start.strftime('%b %Y')} – {last_month_start.strftime('%b %Y')}"
        prev_start = add_months(last_month_start, -months_window).isoformat()
        next_start = add_months(last_month_start, months_window).isoformat()

    # ---------- YEAR VIEW: last 6 years, aggregated per year ----------
    else:  # year
        years_window = 6
        last_year = base.year
        first_year = last_year - (years_window - 1)

        qs = (
            Appointment.objects
            .filter(date__year__gte=first_year, date__year__lte=last_year)
            .values("date__year")
            .annotate(count=Count("id"))
        )
        counts_map = {row["date__year"]: row["count"] for row in qs}

        labels = []
        values = []
        for y in range(first_year, last_year + 1):
            labels.append(str(y))
            values.append(counts_map.get(y, 0))

        period_label = f"{first_year} – {last_year}"
        prev_start = date(first_year - years_window, 1, 1).isoformat()
        next_start = date(last_year + years_window, 1, 1).isoformat()

    data = {
        "view": view_mode,
        "labels": labels,
        "values": values,
        "period_label": period_label,
        "prev_start": prev_start,
        "next_start": next_start,
    }
    return JsonResponse(data)


@login_required
def appointments(request):
    q = request.GET.get("q", "").strip()
    today = timezone.localdate()

    # ---- Handle actions from buttons (Approve / Cancel / Complete etc.) ----
    if request.method == "POST":
        appt_id = request.POST.get("appointment_id")
        action = request.POST.get("action")
        appt = get_object_or_404(Appointment, id=appt_id)

        if action == "approve":
            appt.status = Appointment.STATUS_CONFIRMED
            appt.save()
        elif action == "cancel":
            appt.status = Appointment.STATUS_CANCELLED
            appt.save()
        elif action == "complete":
            appt.status = Appointment.STATUS_COMPLETED
            appt.save()
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
        .order_by("date", "timeslot", "name")
    )

    # Upcoming confirmed appointments (today and future)
    upcoming_appointments = (
        base_qs.filter(
            status=Appointment.STATUS_CONFIRMED,
            date__gte=today,
        )
        .order_by("date", "timeslot", "name")
    )

    # Recent cancelled / completed (history)
    recent_history_qs = (
        base_qs.filter(
            status__in=[Appointment.STATUS_CANCELLED, Appointment.STATUS_COMPLETED]
        )
        .order_by("-date", "timeslot", "name")
    )

    history_page_number = request.GET.get("history_page")
    history_paginator = Paginator(recent_history_qs, 5)
    recent_history = history_paginator.get_page(history_page_number)

    ctx = {
        "q": q,
        "pending_requests": pending_requests,
        "upcoming_appointments": upcoming_appointments,
        "recent_history": recent_history,
        "active_page": "appointments",
    }
    return render(request, "dashboard/pages/dappointments.html", ctx)

@login_required
def patients(request):
	return render(request, 'dashboard/pages/requests.html', {
        "active_page": "patients",
    })

@login_required
def message(request):
	return render(request, 'dashboard/pages/message.html', {
        "active_page": "message",
    })

@login_required
def blog(request):
	return render(request, 'dashboard/pages/blog.html', {
        "active_page": "blog",
    })

@login_required
def profile(request):
	return render(request, 'dashboard/pages/profile.html', {
        "active_page": "profile",
    })

@login_required
def appointment_form(request):
    if request.method == 'POST':
        name = request.POST.get('name').strip()
        phone = request.POST.get('phone').strip()
        email = request.POST.get('email').strip()
        services = request.POST.getlist('services')
        date_str = request.POST.get('appointment_date', '') or request.POST.get('date', '')
        timeslot = request.POST.get('appointment_time', '') or request.POST.get('timeslot', '')

        # Validation
        if not (name and phone and date_str and timeslot and services):
            messages.error(request, 'Please complete name, phone, date, time, and services.')
            return redirect('dashboard:appointment_form')
        
        try:
            app_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect ('dashboard:appointment_form')
        
        # Create appointment
        Appointment.objects.create(
            name=name,
            phone=phone,
            email=email,
            date=app_date,
            services=services,
            timeslot=timeslot,
        )

        messages.success(request, 'Appointment has been created.')
        return redirect('dashboard:appointments')
     
    return render(request, 'dashboard/pages/appointmentform.html', {
        "active_page": "appointments",
    })

