from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage, storages


def get_protected_storage():
    """Dynamically resolve the protected storage backend from django.core.files.storage.storages."""
    try:
        return storages["protected"]
    except KeyError as exc:
        raise ImproperlyConfigured(
            "The 'protected' storage alias is missing from settings.STORAGES."
        ) from exc


class ProtectedFileSystemStorage(FileSystemStorage):
    """Local filesystem backend for private patient documents.
    
    Files are stored under PROTECTED_MEDIA_ROOT (outside public media),
    and direct public URLs are strictly rejected.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", str(settings.PROTECTED_MEDIA_ROOT))
        kwargs["base_url"] = None
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise NotImplementedError(
            "Direct public URLs are disabled for protected patient documents. "
            "Access files through authorized views."
        )


class ProtectedStorageProxy(Storage):
    """Dynamic proxy that delegates the complete Storage API to get_protected_storage().

    Ensures FileField always resolves the active 'protected' storage backend at runtime,
    allowing test overrides via @override_settings(STORAGES=...) to take effect immediately
    without caching a stale backend instance or allowing base Storage methods to intercept calls.
    """

    def _wrapped(self):
        return get_protected_storage()

    def __getattr__(self, name):
        return getattr(self._wrapped(), name)

    def open(self, name, mode="rb"):
        return self._wrapped().open(name, mode=mode)

    def save(self, name, content, max_length=None):
        return self._wrapped().save(name, content, max_length=max_length)

    def get_valid_name(self, name):
        return self._wrapped().get_valid_name(name)

    def get_alternative_name(self, file_root, file_ext):
        return self._wrapped().get_alternative_name(file_root, file_ext)

    def get_available_name(self, name, max_length=None):
        return self._wrapped().get_available_name(name, max_length=max_length)

    def generate_filename(self, filename):
        return self._wrapped().generate_filename(filename)

    def path(self, name):
        return self._wrapped().path(name)

    def delete(self, name):
        return self._wrapped().delete(name)

    def exists(self, name):
        return self._wrapped().exists(name)

    def listdir(self, path):
        return self._wrapped().listdir(path)

    def size(self, name):
        return self._wrapped().size(name)

    def url(self, name):
        return self._wrapped().url(name)

    def get_accessed_time(self, name):
        return self._wrapped().get_accessed_time(name)

    def get_created_time(self, name):
        return self._wrapped().get_created_time(name)

    def get_modified_time(self, name):
        return self._wrapped().get_modified_time(name)

    def deconstruct(self):
        return ("apps.patients.storage.ProtectedStorageProxy", (), {})


# Lazy singleton instance for model FileFields
protected_storage = ProtectedStorageProxy()
