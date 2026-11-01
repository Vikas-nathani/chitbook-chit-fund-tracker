"""Time helpers. All "now" values are in the configured app timezone (IST)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from chitbook_api.core.config import get_settings

_YEAR_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def now() -> datetime:
    """Current timezone-aware datetime in the app timezone."""
    return datetime.now(get_settings().zone)


def today() -> date:
    return now().date()


def to_app_tz(value: datetime) -> datetime:
    return value.astimezone(get_settings().zone)


@dataclass(frozen=True, order=True)
class YearMonth:
    """A calendar month such as 2026-08 (same semantics as java.time.YearMonth)."""

    year: int
    month: int

    @classmethod
    def parse(cls, value: str) -> YearMonth:
        match = _YEAR_MONTH.match(value.strip())
        if not match or not 1 <= int(match.group(2)) <= 12:
            raise ValueError(f"Invalid year-month: {value!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    @classmethod
    def current(cls) -> YearMonth:
        d = today()
        return cls(d.year, d.month)

    def plus_months(self, n: int) -> YearMonth:
        total = self.year * 12 + (self.month - 1) + n
        return YearMonth(total // 12, total % 12 + 1)

    def months_until(self, other: YearMonth) -> int:
        return (other.year * 12 + other.month) - (self.year * 12 + self.month)

    def first_day(self) -> date:
        return date(self.year, self.month, 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
