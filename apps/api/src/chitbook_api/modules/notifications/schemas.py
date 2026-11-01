from __future__ import annotations

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime
from chitbook_api.modules.notifications.models import NotificationStatus


class NotificationOut(ApiModel):
    id: int
    message: str
    type: str
    status: NotificationStatus
    user_id: int
    user_name: str
    created_at: AppDateTime


class UnreadCount(ApiModel):
    count: int


class ConfigCreate(ApiModel):
    chit_group_id: int
    notification_type: str = Field(min_length=1, max_length=50, description="e.g. PAYMENT_REMINDER, LOAN_DUE")
    advance_days: int = Field(ge=0, le=60)
    enabled: bool = True
    message_template: str | None = Field(default=None, max_length=500)
    recurring_day: int | None = Field(default=None, ge=1, le=31)


class ConfigUpdate(ApiModel):
    advance_days: int | None = Field(default=None, ge=0, le=60)
    enabled: bool | None = None
    message_template: str | None = Field(default=None, max_length=500)
    recurring_day: int | None = Field(default=None, ge=1, le=31)


class ConfigOut(ApiModel):
    id: int
    chit_group_id: int
    notification_type: str
    advance_days: int
    enabled: bool
    message_template: str | None
    recurring_day: int | None
    created_at: AppDateTime
    updated_at: AppDateTime
