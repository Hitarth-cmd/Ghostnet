"""
Authentication utilities — JWT + bcrypt.

GHOSTNET_SECRET_KEY must be set in .env (or environment) for production.
The system generates a random key if it is missing and warns loudly so a
developer can't accidentally run without one.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import secrets

import bcrypt
import jwt

logger = logging.getLogger("ghostnet.auth")

_SECRET_KEY = os.environ.get("GHOSTNET_SECRET_KEY") or os.environ.get("SECRET_KEY", "")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "[AUTH] GHOSTNET_SECRET_KEY not set — using ephemeral random key. "
        "All tokens will be invalidated on restart. Set this env var in production."
    )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(data: dict, expires_minutes: int = _ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = {**data, "exp": dt.datetime.utcnow() + dt.timedelta(minutes=expires_minutes)}
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError on bad/expired tokens."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
