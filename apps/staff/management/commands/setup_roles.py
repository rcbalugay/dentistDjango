from django.core.management.base import BaseCommand
from apps.staff.services.role_service import setup_roles_and_permissions


class Command(BaseCommand):
    help = "Idempotently creates standard staff groups and assigns model permissions."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default", help="Database to populate permissions on.")

    def handle(self, *args, **options):
        db = options["database"]
        groups = setup_roles_and_permissions(using=db)
        for name, grp in groups.items():
            perm_count = grp.permissions.count()
            self.stdout.write(self.style.SUCCESS(f"Role '{name}': {perm_count} permissions assigned."))
        self.stdout.write(self.style.SUCCESS("Staff roles successfully initialized."))
