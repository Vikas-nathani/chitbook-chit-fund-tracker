from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import jwt
import pytest

from chitbook_api.core.config import get_settings
from chitbook_api.core.errors import AppError, ErrorCode
from chitbook_api.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    validate_password_strength,
    verify_password,
)
from chitbook_api.core.time import YearMonth, now


class TestYearMonth:
    def test_parse_and_format(self) -> None:
        assert str(YearMonth.parse("2026-08")) == "2026-08"

    @pytest.mark.parametrize("bad", ["2026-13", "2026-8", "26-08", "2026/08", ""])
    def test_rejects_bad_values(self, bad: str) -> None:
        with pytest.raises(ValueError, match="Invalid year-month"):
            YearMonth.parse(bad)

    def test_plus_months_crosses_years(self) -> None:
        assert YearMonth(2026, 11).plus_months(3) == YearMonth(2027, 2)
        assert YearMonth(2026, 1).plus_months(-1) == YearMonth(2025, 12)

    def test_months_until(self) -> None:
        assert YearMonth(2026, 8).months_until(YearMonth(2026, 11)) == 3
        assert YearMonth(2026, 8).months_until(YearMonth(2026, 8)) == 0

    def test_now_is_in_app_timezone(self) -> None:
        assert now().utcoffset() == timedelta(hours=5, minutes=30)


class TestPasswords:
    def test_hash_and_verify(self) -> None:
        hashed = hash_password("Secret123")
        assert hashed.startswith("$argon2id$")
        assert verify_password("Secret123", hashed)
        assert not verify_password("secret123", hashed)

    def test_verify_unknown_user_is_false(self) -> None:
        assert not verify_password("anything1", None)

    @pytest.mark.parametrize(
        ("password", "fragment"),
        [
            ("Ab1", "at least 8"),
            ("password123", "too common"),
            ("abcdefgh", "letter and one number"),
            ("ramesh123", "same as the username"),
        ],
    )
    def test_policy(self, password: str, fragment: str) -> None:
        with pytest.raises(AppError) as exc:
            validate_password_strength(password, "ramesh123")
        assert exc.value.code == ErrorCode.AUTH_WEAK_PASSWORD
        assert fragment in exc.value.message

    def test_policy_accepts_admin_style_password(self) -> None:
        validate_password_strength("Ravi@2026", "ravi")  # 8+ chars, letters + digits


class TestTokens:
    def test_access_token_round_trip(self) -> None:
        family = uuid.uuid4()
        token, expires_in = create_access_token(7, "MEMBER", family)
        claims = decode_access_token(token)
        assert (claims.user_id, claims.role, claims.session_family) == (7, "MEMBER", family)
        assert expires_in == get_settings().access_token_ttl_minutes * 60

    def test_expired_token(self) -> None:
        with patch("chitbook_api.core.security.now", return_value=now() - timedelta(hours=2)):
            token, _ = create_access_token(1, "MEMBER", uuid.uuid4())
        with pytest.raises(AppError) as exc:
            decode_access_token(token)
        assert exc.value.code == ErrorCode.AUTH_TOKEN_EXPIRED

    def test_tampered_or_foreign_token(self) -> None:
        forged = jwt.encode({"sub": "1", "sid": str(uuid.uuid4())}, "wrong-secret", algorithm="HS256")
        with pytest.raises(AppError) as exc:
            decode_access_token(forged)
        assert exc.value.code == ErrorCode.AUTH_TOKEN_INVALID

    def test_refresh_token_is_stored_hashed(self) -> None:
        raw, hashed = new_refresh_token()
        assert raw != hashed
        assert hash_refresh_token(raw) == hashed
        assert len(hashed) == 64
