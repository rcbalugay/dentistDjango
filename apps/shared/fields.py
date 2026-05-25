import os
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet

class FernetEncryptor:
    _fernet = None

    @classmethod
    def get_fernet(cls):
        if cls._fernet is None:
            key = os.getenv("FIELD_ENCRYPTION_KEY")
            if not key:
                # Safe fallback during local runs or test phases
                is_debug = getattr(settings, "DEBUG", True)
                running_tests = getattr(settings, "RUNNING_TESTS", False)
                if not is_debug and not running_tests:
                    raise ValueError("FIELD_ENCRYPTION_KEY environment variable is missing in production!")
                # Fallback dummy key for development/tests
                key = Fernet.generate_key()
            elif isinstance(key, str):
                key = key.encode()
            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, val):
        if val is None or val == "":
            return val
        if not isinstance(val, str):
            val = str(val)
        fernet = cls.get_fernet()
        return fernet.encrypt(val.encode()).decode()

    @classmethod
    def decrypt(cls, val):
        if val is None or val == "":
            return val
        if not isinstance(val, str):
            return val
        
        try:
            fernet = cls.get_fernet()
            return fernet.decrypt(val.encode()).decode()
        except Exception:
            # Fallback to plain text if the value is not encrypted yet (crucial for migration)
            return val

class EncryptedCharField(models.CharField):
    """
    Symmetrically encrypted CharField using AES (Fernet).
    Uses DB TextField to prevent length overflow crashes due to encryption overhead.
    """
    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return FernetEncryptor.decrypt(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            return FernetEncryptor.decrypt(value)
        return super().to_python(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return FernetEncryptor.encrypt(value)


class EncryptedTextField(models.TextField):
    """
    Symmetrically encrypted TextField using AES (Fernet).
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return FernetEncryptor.decrypt(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            return FernetEncryptor.decrypt(value)
        return super().to_python(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return FernetEncryptor.encrypt(value)
