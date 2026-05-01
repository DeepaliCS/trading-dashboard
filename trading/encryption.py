from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    if not value:
        return ''
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ''
    return _fernet().decrypt(value.encode()).decode()
