from __future__ import annotations

from pydantic import Field

from chitbook_api.core.schemas import ApiModel, AppDateTime


class SendMessage(ApiModel):
    content: str = Field(min_length=1, max_length=1000)


class ChatMessageOut(ApiModel):
    id: int
    chit_group_id: int
    sender_id: int
    sender_name: str
    content: str
    message_type: str
    created_at: AppDateTime
