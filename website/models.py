# Legacy compatibility imports. Real model ownership now lives in apps/.
from apps.appointments.models import Appointment
from apps.patients.models import Patient

__all__ = ["Appointment", "Patient"]
