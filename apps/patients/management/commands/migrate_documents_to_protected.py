import hashlib
import os
from django.conf import settings
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from apps.patients.models import PatientDocument
from apps.patients.storage import get_protected_storage


def calculate_sha256(storage, name, chunk_size=65536):
    """Calculate SHA-256 hash and byte size of a file in storage using chunked reads."""
    hasher = hashlib.sha256()
    total_size = 0
    with storage.open(name, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
            total_size += len(chunk)
    return hasher.hexdigest(), total_size


class Command(BaseCommand):
    help = (
        "Physically migrate legacy patient document files from public media storage "
        "to protected storage, verifying contents with chunked SHA-256 hashes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--copy",
            action="store_true",
            help="Copy files from public media to protected storage and verify SHA-256 hashes.",
        )
        parser.add_argument(
            "--delete-source",
            action="store_true",
            help="Delete verified source files from public media storage. Requires --copy.",
        )

    def handle(self, *args, **options):
        copy_mode = options.get("copy", False)
        delete_source = options.get("delete_source", False)

        if delete_source and not copy_mode:
            raise CommandError(
                "The --delete-source flag requires --copy to prevent accidental deletion without verification."
            )

        mode_label = (
            "COPY & DELETE-SOURCE"
            if (copy_mode and delete_source)
            else ("COPY ONLY" if copy_mode else "DRY-RUN (reporting only)")
        )
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Document Migration to Protected Storage ({mode_label}) ==="))

        source_storage = storages["default"]
        dest_storage = get_protected_storage()

        self.stdout.write(f"Source: {getattr(source_storage, 'base_location', 'default')}")
        self.stdout.write(f"Destination: {getattr(dest_storage, 'base_location', 'protected')}")

        # 1. Inventory all PatientDocument records
        documents = PatientDocument.objects.all().order_by("id")
        total_docs = documents.count()
        self.stdout.write(f"Found {total_docs} PatientDocument database record(s).")

        referenced_keys = set()
        already_protected = 0
        copied_and_verified = 0
        missing_source = 0
        conflicts = 0
        source_deleted = 0

        for doc in documents:
            if not doc.file or not doc.file.name:
                continue
            file_key = doc.file.name
            referenced_keys.add(file_key)

            source_exists = source_storage.exists(file_key)
            dest_exists = dest_storage.exists(file_key)

            if dest_exists:
                if source_exists:
                    src_hash, src_size = calculate_sha256(source_storage, file_key)
                    dest_hash, dest_size = calculate_sha256(dest_storage, file_key)

                    if src_hash == dest_hash and src_size == dest_size:
                        already_protected += 1
                        if copy_mode and delete_source:
                            source_storage.delete(file_key)
                            source_deleted += 1
                    else:
                        conflicts += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f"[CONFLICT] File '{file_key}' exists in both source and destination "
                                f"with DIFFERENT hashes. Left untouched."
                            )
                        )
                else:
                    already_protected += 1
            else:
                if source_exists:
                    if copy_mode:
                        src_hash, src_size = calculate_sha256(source_storage, file_key)
                        with source_storage.open(file_key, "rb") as f_in:
                            dest_storage.save(file_key, f_in)

                        dest_hash, dest_size = calculate_sha256(dest_storage, file_key)
                        if src_hash == dest_hash and src_size == dest_size:
                            copied_and_verified += 1
                            if delete_source:
                                source_storage.delete(file_key)
                                source_deleted += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"[VERIFY FAILED] Hash mismatch after copying '{file_key}'. Source NOT deleted."
                                )
                            )
                    else:
                        self.stdout.write(f"[NEEDS COPY] '{file_key}' (size: {source_storage.size(file_key)} bytes)")
                else:
                    missing_source += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[MISSING] Document ID {doc.id} references '{file_key}' but file is missing from both storages."
                        )
                    )

        # 2. Check for unreferenced files under legacy directory 'patient_documents'
        unreferenced_found = 0
        unreferenced_copied = 0
        try:
            source_loc = getattr(source_storage, "base_location", None)
            if source_loc:
                legacy_dir = os.path.join(source_loc, "patient_documents")
                if os.path.exists(legacy_dir):
                    for root, _, filenames in os.walk(legacy_dir):
                        for fn in filenames:
                            full_path = os.path.join(root, fn)
                            rel_key = os.path.relpath(full_path, source_loc).replace("\\", "/")
                            if rel_key not in referenced_keys:
                                unreferenced_found += 1
                                if not dest_storage.exists(rel_key):
                                    if copy_mode:
                                        src_hash, src_size = calculate_sha256(source_storage, rel_key)
                                        with source_storage.open(rel_key, "rb") as f_in:
                                            dest_storage.save(rel_key, f_in)
                                        dest_hash, dest_size = calculate_sha256(dest_storage, rel_key)
                                        if src_hash == dest_hash and src_size == dest_size:
                                            unreferenced_copied += 1
                                            if delete_source:
                                                source_storage.delete(rel_key)
                                                source_deleted += 1
                                    else:
                                        self.stdout.write(
                                            self.style.NOTICE(f"[UNREFERENCED LEGACY] Found '{rel_key}' in public media")
                                        )
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Note: Unreferenced scan encountered: {exc}"))

        # 3. Summary Report
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Migration Summary ==="))
        self.stdout.write(f"Total Database Documents: {total_docs}")
        self.stdout.write(f"Already Protected:        {already_protected}")
        if copy_mode:
            self.stdout.write(f"Copied & Verified:        {copied_and_verified}")
            if unreferenced_copied:
                self.stdout.write(f"Unreferenced Copied:      {unreferenced_copied}")
            if delete_source:
                self.stdout.write(f"Source Files Deleted:     {source_deleted}")
        else:
            pending = total_docs - already_protected - missing_source - conflicts
            self.stdout.write(f"Pending Copy:             {max(0, pending)}")
        self.stdout.write(f"Missing Source Files:     {missing_source}")
        self.stdout.write(f"Destination Conflicts:    {conflicts}")
        if unreferenced_found:
            self.stdout.write(f"Unreferenced Legacy Files:{unreferenced_found}")

        if not copy_mode:
            self.stdout.write(self.style.SUCCESS("\nDry-run complete. Run with --copy to execute migration."))
        else:
            self.stdout.write(self.style.SUCCESS("\nMigration operations completed successfully."))
