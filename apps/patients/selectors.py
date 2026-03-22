from apps.patients.models import Patient


def find_matching_patient(*, name="", phone="", email=""):
    if phone:
        patient = Patient.objects.filter(phone=phone).first()
        if patient:
            return patient

    if email:
        patient = Patient.objects.filter(email=email).first()
        if patient:
            return patient

    if name and phone and email:
        return Patient.objects.filter(
            name__iexact=name,
            phone=phone,
            email=email,
        ).first()

    return None
