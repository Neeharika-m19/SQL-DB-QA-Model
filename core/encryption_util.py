# core/encryption_utils.py

import os
from cryptography.fernet import Fernet
from fastapi import HTTPException


def encrypt_api_key(api_key: str, fernet_key: str) -> str:
    fernet = Fernet(fernet_key.encode())
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str, fernet_key: str) -> str:
    fernet = Fernet(fernet_key.encode())
    return fernet.decrypt(encrypted_key.encode()).decode()

