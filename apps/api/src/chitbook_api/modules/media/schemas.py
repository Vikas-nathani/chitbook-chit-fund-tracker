from __future__ import annotations

from pydantic import Field, HttpUrl

from chitbook_api.core.schemas import ApiModel, AppDateTime
from chitbook_api.modules.media.models import MediaType


class MediaCreate(ApiModel):
    group_id: int
    url: HttpUrl = Field(description="Where the photo/video is hosted (http/https)")
    caption: str = Field(min_length=1, max_length=255)
    media_type: MediaType


class MediaOut(ApiModel):
    id: int
    group_id: int
    uploader_id: int
    uploader_name: str
    url: str
    caption: str
    media_type: MediaType
    created_at: AppDateTime
