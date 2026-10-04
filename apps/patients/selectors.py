from apps.patients.models import Patient
from .normalization import normalize_phone, normalize_email


class PatientConflictError(Exception):
    """
    Raised when submitted phone and email belong to different existing patients.
    """
    pass


def find_patient_by_phone(phone: str):
    norm = normalize_phone(phone)
    if not norm:
        return None
    for patient in Patient.objects.all():
        if normalize_phone(patient.phone) == norm:
            return patient
    return None


def find_patient_by_email(email: str):
    norm = normalize_email(email)
    if not norm:
        return None
    for patient in Patient.objects.all():
        if normalize_email(patient.email) == norm:
            return patient
    return None


def resolve_patient_identity(*, name: str = "", phone: str = "", email: str = ""):
    """
    Resolves patient identity using strict resolution rules:
    - If phone matches Patient A and email matches Patient B: raises PatientConflictError.
    - If both match the same patient: returns that patient.
    - If only one matches: returns that patient.
    - If neither matches: returns None.
    """
    phone_patient = find_patient_by_phone(phone) if phone else None
    email_patient = find_patient_by_email(email) if email else None

    # Conflick check: phone belongs to Patient A, email belongs to Patient B
    if phone_patient and email_patient and phone_patient.pk != email_patient.pk:
        raise PatientConflictError(
            "The provided phone number and email address belong to"
            "different existing patient records."
        )

    return phone_patient or email_patient


def find_matching_patient(*, name="", phone="", email=""):
    """Backwards-compatible wrapper delegating to resolve_patient_identity."""
    return resolve_patient_identity(name=name, phone=phone, email=email)
