"""Shared Pydantic building blocks: camelCase JSON, money and IST datetimes."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from chitbook_api.core.time import to_app_tz


class ApiModel(BaseModel):
    """Base for every request/response body: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# Money is stored as NUMERIC(14,2) and sent as a JSON number
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]

# Timestamps are stored in UTC by Postgres and always returned in the app timezone (+05:30)
AppDateTime = Annotated[
    datetime, PlainSerializer(lambda v: to_app_tz(v).isoformat(), return_type=str, when_used="json")
]
