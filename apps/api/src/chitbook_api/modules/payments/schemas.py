from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money
from chitbook_api.modules.payments.models import PaymentStatus


class PaymentCreate(ApiModel):
    user_id: int = Field(description="Member who paid (yourself unless you are a group admin/accountant)")
    chit_group_id: int
    month: str = Field(min_length=1, max_length=15, description="e.g. 2026-08")
    amount_paid: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_date: datetime | None = Field(default=None, description="Default now")
    mode: str = Field(min_length=1, max_length=20, description="CASH, UPI, BANK_TRANSFER, ...")


class PaymentStatusUpdate(ApiModel):
    status: PaymentStatus


class PaymentOut(ApiModel):
    id: int
    month: str
    amount_paid: Money
    payment_date: AppDateTime
    mode: str
    status: PaymentStatus
    user_id: int
    user_name: str
    chit_group_id: int
    chit_group_name: str
    verified: bool
    verified_by_user_id: int | None
    verified_by_user_name: str | None
    verified_at: AppDateTime | None
    created_at: AppDateTime
    updated_at: AppDateTime
