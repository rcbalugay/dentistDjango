import os
import hmac
import hashlib
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Raised when ciphertext cannot be decrypted with the active key."""
    pass

def get_field_encryption_key() -> bytes:
    """Retrieves and validates the mandatory FIELD_ENCRYPTION_KEY."""
    raw_key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not raw_key or not raw_key.strip():
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY environment variable is mandatory and missing.")
    key = raw_key.strip()
    return key.encode("utf-8") if isinstance(key, str) else key
def compute_lookup_hash(val: str) -> str:
    """Compute a deterministic HMAC-SHA256 digest for indexed lookups."""
    if not val or not val.strip():
        return ""
    key = get_field_encryption_key()
    return hmac.new(key, val.strip().encode("utf-8"), hashlib.sha256).hexdigest()


class FernetEncryptor:
    _fernet = None

    @classmethod
    def get_fernet(cls):
        if cls._fernet is None:
            key = get_field_encryption_key()
            cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, val):
        if val is None or val == "":
            return val
        if not isinstance(val, str):
            val = str(val)
        fernet = cls.get_fernet()
        return fernet.encrypt(val.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, val):
        if val is None or val == "":
            return val
        if not isinstance(val, str):
            val = str(val)
        try:
            fernet = cls.get_fernet()
            return fernet.decrypt(val.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError, UnicodeDecodeError) as e:
            raise DecryptionError(
                "Failed to decrypt ciphertext with active encryption key."
            ) from e

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
        if isinstance(value, str) and value.startswith("gAAAA"):
            return FernetEncryptor.decrypt(value)
        return value


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
        if isinstance(value, str) and value.startswith("gAAAA"):
            return FernetEncryptor.decrypt(value)
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return FernetEncryptor.encrypt(value)
