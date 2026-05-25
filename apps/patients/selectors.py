from apps.patients.models import Patient


def find_matching_patient(*, name="", phone="", email=""):
    # Since phone and email are symmetrically encrypted with non-deterministic Fernet,
    # direct database queries with SQL filter(phone=phone) will fail to match.
    # We instead retrieve patients and perform plaintext comparisons in Python memory.
    if phone:
        for patient in Patient.objects.all():
            if patient.phone == phone:
                return patient

    if email:
        for patient in Patient.objects.all():
            if patient.email == email:
                return patient

    if name and phone and email:
        for patient in Patient.objects.filter(name__iexact=name):
            if patient.phone == phone and patient.email == email:
                return patient

    return None
