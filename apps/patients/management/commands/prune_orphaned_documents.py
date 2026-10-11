import logging
import os
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.patients.models import PatientDocument
from apps.patients.storage import get_protected_storage

logger = logging.getLogger(__name__)

RECOGNIZED_PREFIXES = ("patients/", "patient_documents/")


class Command(BaseCommand):
    help = (
        "Identify and safely prune storage files in protected storage that are "
        "no longer referenced by any PatientDocument database record."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete unreferenced orphaned files. Defaults to dry-run reporting.",
        )
        parser.add_argument(
            "--min-age-minutes",
            type=int,
            default=60,
            help="Minimum object age in minutes before a file is eligible for pruning (default: 60).",
        )

    def handle(self, *args, **options):
        do_delete = options.get("delete", False)
        min_age_minutes = options.get("min_age_minutes", 60)

        mode_str = "DELETE MODE" if do_delete else "DRY-RUN (reporting only)"
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Orphaned Document Reconciliation ({mode_str}) ==="))

        storage = get_protected_storage()
        storage_location = getattr(storage, "base_location", "protected")
        self.stdout.write(f"Protected Storage: {storage_location}")
        self.stdout.write(f"Scanning Prefixes: {', '.join(RECOGNIZED_PREFIXES)}")
        self.stdout.write(f"Age Threshold:     {min_age_minutes} minutes")

        # 1. Collect all referenced file keys from the database
        referenced_keys = set(
            PatientDocument.objects.exclude(file="").values_list("file", flat=True)
        )
        self.stdout.write(f"Active database references: {len(referenced_keys)}")

        # 2. Walk protected storage for recognized prefixes
        found_files = []
        if hasattr(storage, "base_location") and os.path.exists(storage.base_location):
            base_dir = storage.base_location
            for prefix in RECOGNIZED_PREFIXES:
                prefix_dir = os.path.join(base_dir, prefix)
                if os.path.exists(prefix_dir):
                    for root, _, filenames in os.walk(prefix_dir):
                        for fn in filenames:
                            full_path = os.path.join(root, fn)
                            rel_key = os.path.relpath(full_path, base_dir).replace("\\", "/")
                            found_files.append(rel_key)

        self.stdout.write(f"Total files found under recognized prefixes: {len(found_files)}")

        now = timezone.now()
        age_cutoff = now - timedelta(minutes=min_age_minutes)

        referenced_count = 0
        too_recent_count = 0
        timestamp_unsupported_count = 0
        orphans_found = []
        deleted_count = 0
        failed_count = 0

        for rel_key in found_files:
            if rel_key in referenced_keys:
                referenced_count += 1
                continue

            # Check file modification time safely
            try:
                mtime = storage.get_modified_time(rel_key)
                if timezone.is_naive(mtime):
                    mtime = timezone.make_aware(mtime)

                if mtime > age_cutoff:
                    too_recent_count += 1
                    self.stdout.write(
                        self.style.NOTICE(
                            f"[RECENT] Unreferenced but within age threshold: '{rel_key}' (modified: {mtime})"
                        )
                    )
                    continue
            except (NotImplementedError, AttributeError) as exc:
                timestamp_unsupported_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[TIMESTAMP UNSUPPORTED] Backend cannot provide mtime for '{rel_key}': {exc}"
                    )
                )

            orphans_found.append(rel_key)

            if do_delete:
                try:
                    storage.delete(rel_key)
                    deleted_count += 1
                    logger.info("Pruned orphaned document file: %s", rel_key)
                    self.stdout.write(self.style.SUCCESS(f"[DELETED] '{rel_key}'"))
                except Exception as exc:
                    failed_count += 1
                    logger.warning("Failed to delete orphaned document file '%s': %s", rel_key, exc)
                    self.stdout.write(self.style.ERROR(f"[FAILED] '{rel_key}': {exc}"))
            else:
                self.stdout.write(self.style.WARNING(f"[ORPHAN CANDIDATE] '{rel_key}'"))

        # 3. Summary report
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Reconciliation Summary ==="))
        self.stdout.write(f"Total Scanned Files:         {len(found_files)}")
        self.stdout.write(f"Referenced (In Use):         {referenced_count}")
        self.stdout.write(f"Recent (Protected by age):   {too_recent_count}")
        if timestamp_unsupported_count:
            self.stdout.write(f"Timestamp Unsupported:       {timestamp_unsupported_count}")
        self.stdout.write(f"Orphan Candidates:           {len(orphans_found)}")
        if do_delete:
            self.stdout.write(self.style.SUCCESS(f"Successfully Deleted:        {deleted_count}"))
            if failed_count:
                self.stdout.write(self.style.ERROR(f"Failed Deletions:            {failed_count}"))
        else:
            self.stdout.write(self.style.SUCCESS("Dry-run complete. Pass --delete to prune candidate files."))
