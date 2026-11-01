"""Password hashing (Argon2id), JWT access tokens and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from chitbook_api.core.config import get_settings
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.time import now

_hasher = PasswordHasher()  # Argon2id with library-recommended parameters

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890", "qwerty123",
    "qwertyuiop", "11111111", "00000000", "iloveyou", "admin123", "welcome1", "letmein1",
    "abc12345", "passw0rd", "chitfund", "chitbook", "india123", "india@123",
}  # fmt: skip

# Used to keep login timing identical when the username does not exist
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def validate_password_strength(password: str, username: str | None = None) -> None:
    problems: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"must be at most {PASSWORD_MAX_LENGTH} characters")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("is too common")
    if username and password.lower() == username.lower():
        problems.append("must not be the same as the username")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        problems.append("must contain at least one letter and one number")
    if problems:
        raise AppError(ErrorCode.AUTH_WEAK_PASSWORD, "Password " + "; ".join(problems), details=problems)


@dataclass(frozen=True)
class AccessClaims:
    user_id: int
    role: str
    session_family: uuid.UUID
    token_id: str


def create_access_token(user_id: int, role: str, session_family: uuid.UUID) -> tuple[str, int]:
    """Returns (jwt, expires_in_seconds)."""
    s = get_settings()
    issued = now()
    ttl = timedelta(minutes=s.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "sid": str(session_family),
        "jti": uuid.uuid4().hex,
        "iss": s.jwt_issuer,
        "iat": int(issued.timestamp()),
        "exp": int((issued + ttl).timestamp()),
        "typ": "access",
    }
    token = jwt.encode(payload, s.jwt_secret.get_secret_value(), algorithm="HS256")
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> AccessClaims:
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=s.jwt_issuer,
            options={"require": ["sub", "sid", "exp", "iat", "iss", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.AUTH_TOKEN_EXPIRED) from exc
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID) from exc
    if payload.get("typ") != "access":
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID)
    try:
        return AccessClaims(
            int(payload["sub"]), str(payload["role"]), uuid.UUID(payload["sid"]), payload["jti"]
        )
    except (ValueError, KeyError) as exc:
        raise AppError(ErrorCode.AUTH_TOKEN_INVALID) from exc


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw token for the client, sha256 hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
