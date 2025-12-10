from datetime import date, timedelta
from django.db.models import Count
from website.models import Appointment


def _add_months(d: date, n: int) -> date:
    """Return a date n months from d (always day=1)."""
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def build_appointment_chart(view_mode: str, base: date):
    """
    Core logic for building chart labels/values and navigation
    for daily / weekly / monthly / yearly appointment stats.
    """
    view_mode = (view_mode or "day").lower()
    if view_mode not in {"day", "week", "month", "year"}:
        view_mode = "day"

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

    # ---------- WEEK VIEW: 4 weekly buckets ----------
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

        labels = [f"Week {i+1}" for i in range(weeks_window)]
        values = week_counts

        period_label = f"{period_start.strftime('%d %b')} – {period_end.strftime('%d %b %Y')}"
        prev_start = (period_start - timedelta(days=days_window)).isoformat()
        next_start = (period_end + timedelta(days=days_window)).isoformat()

    # ---------- MONTH VIEW: up to 6 months ----------
    elif view_mode == "month":
        months_window = 6
        last_month_start = base.replace(day=1)
        first_month_start = _add_months(last_month_start, -(months_window - 1))

        month_starts = [_add_months(first_month_start, i) for i in range(months_window)]
        last_month_end = _add_months(last_month_start, 1) - timedelta(days=1)

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
        prev_start = _add_months(last_month_start, -months_window).isoformat()
        next_start = _add_months(last_month_start, months_window).isoformat()

    # ---------- YEAR VIEW: last 6 years ----------
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

    return {
        "view": view_mode,
        "labels": labels,
        "values": values,
        "period_label": period_label,
        "prev_start": prev_start,
        "next_start": next_start,
    }
