from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money
from chitbook_api.modules.groups.models import GroupRole, GroupStatus, MembershipStatus


class GroupCreate(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    duration: int = Field(ge=1, le=120, description="Months")
    monthly_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    total_members: int = Field(ge=1, le=500, description="Member limit")
    start_date: datetime | None = Field(default=None, description="Default now")


class GroupUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    duration: int | None = Field(default=None, ge=1, le=120)
    monthly_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    total_members: int | None = Field(default=None, ge=1, le=500)
    start_date: datetime | None = None


class GroupStatusUpdate(ApiModel):
    status: GroupStatus


class GroupOut(ApiModel):
    id: int
    group_code: str
    name: str
    duration: int
    monthly_amount: Money
    total_members: int
    start_date: AppDateTime
    status: GroupStatus
    fund_id: int | None
    created_at: AppDateTime
    updated_at: AppDateTime


class JoinRequest(ApiModel):
    group_code: str = Field(min_length=4, max_length=20)


class AddMemberRequest(ApiModel):
    user_id: int


class MembershipStatusUpdate(ApiModel):
    status: MembershipStatus


class MembershipOut(ApiModel):
    id: int
    user_id: int
    user_name: str
    chit_group_id: int
    chit_group_name: str
    chit_group_code: str
    monthly_amount: Money
    duration: int
    total_members: int
    start_date: AppDateTime
    join_date: AppDateTime
    status: MembershipStatus
    role: GroupRole
