from typing import Optional, Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache

from website.models import Appointment
from dashboard.utils.weather import client_ip, ip_for_query, weather_by_ip


def get_cached_weather(request, ttl_seconds: int = 300) -> Optional[Dict]:
    """
    Weather for dashboard header, cached for ttl_seconds.
    Cache key is based on ip_for_query(ip) so localhost/private IP becomes stable.
    """
    if not settings.WEATHERAPI_KEY:
        return None

    ip = client_ip(request)
    q = ip_for_query(ip)
    cache_key = f"weather:{q}"

    wx = cache.get(cache_key)
    if wx is None:
        wx = weather_by_ip(ip)
        if wx:
            cache.set(cache_key, wx, ttl_seconds)
    return wx


def get_latest_appointments(limit: int = 5) -> List[Appointment]:
    """
    Latest Patients widget (for now): show latest COMPLETED appointments.
    De-dupe by (phone,email,name) so same person doesn't appear repeatedly.
    """
    completed_qs = (
        Appointment.objects
        .filter(status=Appointment.STATUS_COMPLETED)
        .order_by("-date", "-start_time", "-id")
    )

    latest: List[Appointment] = []
    seen: set[Tuple[str, str, str]] = set()

    for a in completed_qs:
        key = (
            (a.phone or "").strip(),
            (a.email or "").strip(),
            (a.name or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        latest.append(a)
        if len(latest) >= limit:
            break

    return latest
