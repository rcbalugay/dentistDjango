from django.conf import settings
from django.core.files.storage import FileSystemStorage

class ProtectedFileSystemStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", str(settings.PROTECTED_MEDIA_ROOT))
        kwargs.setdefault("base_url", settings.PROTECTED_MEDIA_URL)
        super().__init__(*args, **kwargs)

protected_storage = ProtectedFileSystemStorage()
