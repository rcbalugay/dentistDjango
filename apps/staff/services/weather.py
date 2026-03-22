import ipaddress
import requests as http_requests
from django.conf import settings

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