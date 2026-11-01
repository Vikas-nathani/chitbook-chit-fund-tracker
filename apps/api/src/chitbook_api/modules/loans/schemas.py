from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime, Money
from chitbook_api.modules.loans.models import LoanStatus


class LoanCreate(ApiModel):
    user_id: int
    chit_group_id: int
    principal: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    interest_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2, description="Annual %")
    tenure_months: Decimal = Field(gt=0, le=240, max_digits=6, decimal_places=2)
    start_date: datetime | None = Field(default=None, description="Default now")
    end_date: datetime | None = None


class LoanStatusUpdate(ApiModel):
    status: LoanStatus


class LoanOut(ApiModel):
    id: int
    principal: Money
    interest_rate: Money
    tenure_months: Money
    current_payable: Money = Field(description="Principal + simple daily interest up to today")
    start_date: AppDateTime
    end_date: AppDateTime | None
    status: LoanStatus
    chit_group_id: int
    chit_group_name: str
    chit_group_code: str
    user_id: int
    user_name: str
    created_at: AppDateTime
    updated_at: AppDateTime


class LoanSummaryOut(ApiModel):
    loan_id: int
    chit_group_id: int
    chit_group_name: str
    chit_group_code: str
    principal: Money
    current_payable: Money
    status: LoanStatus
    days_remaining: int | None


class PayableOut(ApiModel):
    loan_id: int
    current_payable: Money
