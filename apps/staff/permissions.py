from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

# Role Name Constants
ROLE_ADMINISTRATOR = "Administrator"
ROLE_DENTIST = "Dentist"
ROLE_RECEPTIONIST = "Receptionist"
ALL_STAFF_ROLES = (ROLE_ADMINISTRATOR, ROLE_DENTIST, ROLE_RECEPTIONIST)


# ---------------------------------------------------------------------------
# Role Membership Checks
# ---------------------------------------------------------------------------

def is_administrator(user) -> bool:
    """
    Returns True if user is an active staff account with Administrator role
    or is a Django superuser.
    """
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (user.is_superuser or user.groups.filter(name=ROLE_ADMINISTRATOR).exists())
    )


def is_dentist(user) -> bool:
    """
    Returns True if user is an active staff account with Dentist role
    (Administrators automatically inherit dentist clinical privileges).
    """
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (is_administrator(user) or user.groups.filter(name=ROLE_DENTIST).exists())
    )


def is_receptionist(user) -> bool:
    """
    Returns True if user is an active staff account with Receptionist role
    (Administrators automatically inherit receptionist front-desk privileges).
    """
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (is_administrator(user) or user.groups.filter(name=ROLE_RECEPTIONIST).exists())
    )


def is_active_staff(user) -> bool:
    """
    Returns True if user is an active staff account belonging to at least ONE
    recognized staff role group (or is a superuser).
    An account with is_staff=True but NO recognized role returns False.
    """
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and (user.is_superuser or user.groups.filter(name__in=ALL_STAFF_ROLES).exists())
    )


# ---------------------------------------------------------------------------
# Capability Helpers
# ---------------------------------------------------------------------------

def can_view_patient_documents(user) -> bool:
    """Dentists and Administrators can view patient documents and insurance."""
    return is_dentist(user)


def can_upload_patient_documents(user) -> bool:
    """Dentists and Administrators can upload patient documents and insurance."""
    return is_dentist(user)


def can_delete_patient_documents(user) -> bool:
    """Only Administrators can delete patient documents."""
    return is_administrator(user)


def can_manage_content(user) -> bool:
    """Only Administrators can manage site content, blog, team, and settings."""
    return is_administrator(user)


# ---------------------------------------------------------------------------
# Authorization Decorators
# ---------------------------------------------------------------------------

def staff_role_required(*allowed_roles, login_url="dashboard:login"):
    """
    Decorator enforcing role-based staff access:
    - Unauthenticated users -> 302 redirect to login_url.
    - Authenticated non-staff or unrecognized staff (no role) -> 403 PermissionDenied.
    - Active staff with allowed role (or superuser/admin) -> execute view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(login_url)

            if not user.is_active or not user.is_staff:
                raise PermissionDenied("Active staff credentials required.")

            if user.is_superuser or user.groups.filter(name=ROLE_ADMINISTRATOR).exists():
                return view_func(request, *args, **kwargs)

            if any(user.groups.filter(name=role).exists() for role in allowed_roles):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("You do not have permission to access this resource.")
        return _wrapped_view
    return decorator


def active_staff_required(view_func):
    """Allows any active staff member with a recognized role (or superuser)."""
    return staff_role_required(*ALL_STAFF_ROLES)(view_func)


def admin_required(view_func):
    """Restricts access to Administrators and superusers."""
    return staff_role_required(ROLE_ADMINISTRATOR)(view_func)


def dentist_or_admin_required(view_func):
    """Restricts access to Dentists, Administrators, and superusers."""
    return staff_role_required(ROLE_DENTIST, ROLE_ADMINISTRATOR)(view_func)


def receptionist_or_admin_required(view_func):
    """Restricts access to Receptionists, Administrators, and superusers."""
    return staff_role_required(ROLE_RECEPTIONIST, ROLE_ADMINISTRATOR)(view_func)
