from datetime import date, time

# Modify this to add or remove  services 
# offered by the dental clinic

APPOINTMENT_SERVICES = [
    "Consultation",
    "Diagnostics",
    "Whitening",
    "Therapy",
    "Surgery",
    "Orthodontics",
    "Prosthetics",
    "Children's dentistry",
]

SAME_DAY_BOOKING_CUTOFF_HOURS = 2

CLINIC_OPEN_WEEKDAYS = {0, 2, 5, 6}
CLINIC_OPEN_DAYS_LABEL = "Monday, Wednesday, Saturday, and Sunday"

CLINIC_SLOT_TIMES = [time(hour, 0) for hour in range(9, 18)]
CLINIC_SLOT_TIME_SET = set(CLINIC_SLOT_TIMES)

CLINIC_HOLIDAYS = {
    date(2026, 1, 1): "New Year's Day",
    date(2026, 12, 25): "Christmas Day",
}