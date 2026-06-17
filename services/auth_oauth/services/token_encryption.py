"""
Auth/services/token_encryption.py

Encrypts platform OAuth tokens before storing in DB.
Uses Fernet symmetric encryption — key derived from JWT_SECRET for MVP.
In production: use a dedicated KMS key (AWS KMS, Google Cloud KMS).
"""
import base64
from cryptography.fernet import Fernet
from services.auth_oauth.config import settings


def _get_fernet() -> Fernet:
    # Derive a 32-byte Fernet key from JWT_SECRET
    key = base64.urlsafe_b64encode(settings.JWT_SECRET[:32].encode().ljust(32, b"0"))
    return Fernet(key)


def encrypt_token(plain_token: str) -> str:
    return _get_fernet().encrypt(plain_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return _get_fernet().decrypt(encrypted_token.encode()).decode()