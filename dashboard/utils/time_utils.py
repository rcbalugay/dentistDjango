from datetime import datetime, time

DISPLAY_FORMAT = "%I:%M %p"      # '10:00 AM'
INPUT_FORMATS = ("%I:%M %p", "%H:%M")  # what we accept in parse_timeslot


def format_html_time_to_timeslot(time_str: str) -> str:
    """
    Convert <input type="time"> value 'HH:MM' to display string 'h:MM AM/PM'.
    Used in dashboard appointment_form when saving timeslot.
    """
    if not time_str:
        return ""

    time_str = time_str.strip()

    # If it already has AM/PM, just normalize and return
    upper = time_str.upper()
    if "AM" in upper or "PM" in upper:
        try:
            t = datetime.strptime(upper, "%I:%M %p").time()
            return t.strftime(DISPLAY_FORMAT).lstrip("0")
        except ValueError:
            return time_str  # fallback

    # Otherwise assume 'HH:MM' 24-hour from <input type="time">
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        return t.strftime(DISPLAY_FORMAT).lstrip("0")
    except ValueError:
        return time_str  # fallback


def parse_timeslot(ts: str) -> time:
    """
    Convert timeslot strings like '10:00 AM' or '09:30' into a time object,
    so we can sort appointments by time.
    """
    if not ts:
        return time(0, 0)

    ts = ts.strip()
    for fmt in INPUT_FORMATS:
        try:
            return datetime.strptime(ts, fmt).time()
        except ValueError:
            continue

    return time(0, 0)

def parse_date(value):
    """
    Parse a date string in 'YYYY-MM-DD' format into a date object.
    Returns None if parsing fails.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except(TypeError, ValueError):
        return None
