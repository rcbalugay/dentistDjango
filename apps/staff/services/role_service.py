import logging
from django.contrib.auth.models import Group, Permission
from apps.staff.permissions import (
    ROLE_ADMINISTRATOR,
    ROLE_DENTIST,
    ROLE_RECEPTIONIST,
    ALL_STAFF_ROLES,
)

logger = logging.getLogger(__name__)


def setup_roles_and_permissions(using=None):
    """
    Idempotently ensures all three staff Groups exist and assigns appropriate
    Django model permissions on the specified database.
    Safe to run repeatedly during post_migrate and manual command invocations.
    """
    db = using or "default"
    groups = {
        role: Group.objects.using(db).get_or_create(name=role)[0]
        for role in ALL_STAFF_ROLES
    }

    def get_perms(perm_specs):
        found = []
        for app_label, codename in perm_specs:
            p = Permission.objects.using(db).filter(content_type__app_label=app_label, codename=codename).first()
            if p:
                found.append(p)
            else:
                logger.debug("Permission %s.%s not found yet on database '%s'; skipping.", app_label, codename, db)
        return found

    # Dentist permissions (clinical operations)
    # Strictly NO delete_patientdocument (deletion is Administrator-only)
    dentist_perms = get_perms([
        ("appointments", "view_appointment"),
        ("appointments", "add_appointment"),
        ("appointments", "change_appointment"),
        ("patients", "view_patient"),
        ("patients", "change_patient"),
        ("patients", "view_patientdocument"),
        ("patients", "add_patientdocument"),
        ("patients", "change_patientdocument"),
    ])

    # Receptionist permissions (front-desk operations)
    # Strictly NO change_patient (protects clinical notes) and NO patientdocument permissions!
    receptionist_perms = get_perms([
        ("appointments", "view_appointment"),
        ("appointments", "add_appointment"),
        ("appointments", "change_appointment"),
        ("patients", "view_patient"),
        ("patients", "add_patient"),
    ])

    # Administrator permissions (all application permissions)
    admin_perms = list(Permission.objects.using(db).filter(
        content_type__app_label__in=["appointments", "patients", "public", "auth"]
    ))

    groups[ROLE_DENTIST].permissions.set(dentist_perms)
    groups[ROLE_RECEPTIONIST].permissions.set(receptionist_perms)
    groups[ROLE_ADMINISTRATOR].permissions.set(admin_perms)

    return groups


def assign_staff_role(user, role_name):
    """
    Assigns a user to a specific staff role, enforcing mutual exclusivity
    among the standard staff groups and ensuring is_staff=True.
    """
    if role_name not in ALL_STAFF_ROLES:
        raise ValueError(
            f"Unknown staff role '{role_name}'. Allowed roles: {', '.join(ALL_STAFF_ROLES)}"
        )

    target_group, _ = Group.objects.get_or_create(name=role_name)

    # Remove existing staff role groups to enforce single-role exclusivity
    existing_staff_groups = Group.objects.filter(name__in=ALL_STAFF_ROLES)
    user.groups.remove(*existing_staff_groups)

    # Add target role group
    user.groups.add(target_group)
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])

    return user
