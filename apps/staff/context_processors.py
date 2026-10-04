from apps.staff.permissions import (
    is_administrator,
    is_dentist,
    is_receptionist,
    can_view_patient_documents,
    can_upload_patient_documents,
)


def staff_roles(request):
    """
    Exposes role and document capability flags for UI conditional rendering.
    UI adjustments are visual conveniences only; all enforcement remains backend server-side.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}

    return {
        "is_admin": is_administrator(user),
        "is_dentist": is_dentist(user),
        "is_receptionist": is_receptionist(user),
        "can_view_documents": can_view_patient_documents(user),
        "can_upload_documents": can_upload_patient_documents(user),
    }
