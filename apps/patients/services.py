from apps.patients.models import Patient

from .selectors import find_matching_patient


def get_or_create_patient_record(*, name="", phone="", email=""):
    patient = find_matching_patient(name=name, phone=phone, email=email)

    if not patient and (name or phone or email):
        patient = Patient.objects.create(
            name=name,
            phone=phone,
            email=email,
        )

    if not patient:
        return None

    changed_fields = []

    if name and patient.name != name:
        patient.name = name
        changed_fields.append("name")

    if phone and patient.phone != phone:
        patient.phone = phone
        changed_fields.append("phone")

    if email and patient.email != email:
        patient.email = email
        changed_fields.append("email")

    if changed_fields:
        patient.save(update_fields=changed_fields)

    return patient
