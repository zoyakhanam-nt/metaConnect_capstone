import os
import time

import requests
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "metaconnect")

_JWKS_URL = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 300

bearer_scheme = HTTPBearer()

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "change-me-internal-key")


def _get_jwks() -> dict:
    now = time.time()
    if _jwks_cache["keys"] is None or (now - _jwks_cache["fetched_at"]) > _JWKS_TTL_SECONDS:
        resp = requests.get(_JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache["keys"] = resp.json()
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    token = credentials.credentials

    try:
        jwks = _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)

        if key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")

        payload = jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


def verify_internal_api_key(x_internal_api_key: str = Header(...)) -> None:
    if x_internal_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")