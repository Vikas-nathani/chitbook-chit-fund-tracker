from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime
from chitbook_api.modules.users.schemas import UserOut


class ClientType(StrEnum):
    MOBILE = "mobile"  # refresh token returned in the body, stored in Keychain/Keystore
    WEB = "web"  # refresh token set as an HttpOnly cookie, never visible to JavaScript


class LoginRequest(ApiModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)
    device_name: str | None = Field(default=None, max_length=100, description="Shown in the sessions list")
    client: ClientType = ClientType.MOBILE


class RefreshRequest(ApiModel):
    refresh_token: str | None = Field(default=None, description="Mobile only; web sends the cookie")
    client: ClientType = ClientType.MOBILE


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "Bearer"  # noqa: S105 - token scheme name, not a secret
    expires_in: int = Field(description="Access token lifetime in seconds")
    refresh_token: str | None = Field(description="Null for web clients (cookie is used instead)")
    refresh_expires_at: AppDateTime
    user: UserOut


class SessionOut(ApiModel):
    id: uuid.UUID = Field(description="Session (device) id; use it to sign that device out")
    device_name: str | None
    user_agent: str | None
    ip_address: str | None
    signed_in_at: AppDateTime
    last_used_at: AppDateTime | None
    expires_at: AppDateTime
    current: bool
