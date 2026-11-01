from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money
from chitbook_api.modules.ledger.models import EntryType


class LedgerCreate(ApiModel):
    user_id: int
    chit_group_id: int
    entry_type: EntryType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    entry_date: datetime | None = Field(default=None, description="Default now")
    remark: str | None = Field(default=None, max_length=255)
    reference_id: str | None = Field(default=None, max_length=50, description="Related payment/auction id")


class LedgerOut(ApiModel):
    id: int
    entry_type: EntryType
    amount: Money
    entry_date: AppDateTime
    remark: str | None
    reference_id: str | None
    user_id: int
    user_name: str
    chit_group_id: int
    chit_group_name: str
    created_at: AppDateTime
    updated_at: AppDateTime
