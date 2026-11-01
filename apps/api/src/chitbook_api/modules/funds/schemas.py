from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money


class FundOut(ApiModel):
    id: int
    name: str
    total_amount: Money
    cycle_period: int
    interest_rate: Money
    chit_group_id: int
    chit_group_name: str
    created_at: AppDateTime
    updated_at: AppDateTime


class FundUpdate(ApiModel):
    total_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    interest_rate: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
