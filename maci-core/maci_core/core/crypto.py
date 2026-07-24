import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from maci_core.config import settings

def _get_fernet() -> Fernet:
    """
    Derives a Fernet encryption key from the SECRET_KEY setting using PBKDF2.
    This ensures AES-128 encryption (Fernet uses AES-128-CBC) for PII data.
    """
    password = settings.SECRET_KEY.encode()
    salt = b'maci_zero_knowledge_salt_v1'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def encrypt_pii(data: str) -> str:
    """Encrypts plaintext PII data into a secure vault string."""
    if not data:
        return data
    f = _get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_pii(encrypted_data: str) -> str:
    """Decrypts a secure vault string back into plaintext."""
    if not encrypted_data:
        return encrypted_data
    f = _get_fernet()
    return f.decrypt(encrypted_data.encode()).decode()
