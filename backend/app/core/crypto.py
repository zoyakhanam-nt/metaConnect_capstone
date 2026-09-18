from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_ENCRYPTION_KEY = get_settings().encryption_key
_fernet = Fernet(_ENCRYPTION_KEY.encode())


def encrypt_value(plain: str) -> str:
    if plain == "":
        return ""
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    if token == "":
        return ""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Stored value could not be decrypted — ENCRYPTION_KEY may have changed")


# kept as aliases so nothing else needs renaming
encrypt_password = encrypt_value
decrypt_password = decrypt_value