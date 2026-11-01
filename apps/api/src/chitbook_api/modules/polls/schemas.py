from __future__ import annotations

from datetime import datetime

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime
from chitbook_api.modules.polls.models import PollStatus


class PollCreate(ApiModel):
    group_id: int
    question: str = Field(min_length=1, max_length=255)
    options: list[str] = Field(min_length=2, max_length=10)
    expires_at: datetime | None = None


class VoteRequest(ApiModel):
    poll_id: int
    option_id: int


class PollOptionOut(ApiModel):
    id: int
    option_text: str
    vote_count: int


class PollOut(ApiModel):
    id: int
    group_id: int
    group_name: str
    creator_id: int
    creator_name: str
    question: str
    status: PollStatus
    expires_at: AppDateTime | None
    created_at: AppDateTime
    options: list[PollOptionOut]
    my_vote_option_id: int | None
