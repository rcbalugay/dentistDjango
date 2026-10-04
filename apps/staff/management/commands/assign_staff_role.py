from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from apps.staff.permissions import ALL_STAFF_ROLES
from apps.staff.services.role_service import assign_staff_role


class Command(BaseCommand):
    help = "Assigns a user to a specific staff role (Administrator, Dentist, Receptionist)."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username of the user account")
        parser.add_argument("role", type=str, choices=ALL_STAFF_ROLES, help="Role name to assign")

    def handle(self, *args, **options):
        username = options["username"]
        role = options["role"]
        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        assign_staff_role(user, role)
        self.stdout.write(self.style.SUCCESS(f"Successfully assigned user '{username}' to role '{role}'."))
