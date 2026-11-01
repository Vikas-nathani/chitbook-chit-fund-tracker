from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money


class AuctionCreate(ApiModel):
    chit_group_id: int
    winning_member_id: int = Field(description="User id of the winner (must be an active member)")
    month: str = Field(
        min_length=1, max_length=20, description="e.g. 2026-08; one auction per month per group"
    )
    winning_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    commission: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    auction_date: datetime | None = Field(default=None, description="Default now")
    remark: str | None = Field(default=None, max_length=200)


class AuctionOut(ApiModel):
    id: int
    month: str
    winning_amount: Money
    commission: Money
    auction_date: AppDateTime
    remark: str | None
    winning_member_id: int
    winning_member_name: str
    chit_group_id: int
    chit_group_name: str
    created_at: AppDateTime
    updated_at: AppDateTime
