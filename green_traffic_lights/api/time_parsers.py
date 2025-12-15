from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional


def parse_timestamp(timestamp_raw: str) -> Optional[datetime]:
    try:
        timestamp_clean = timestamp_raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(timestamp_clean)
        if parsed.tzinfo is None:
            raise ValueError("Timestamp must be timezone aware")
        return parsed.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        return None


def parse_date(date_raw: str) -> Optional[date]:
    try:
        return datetime.strptime(date_raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


class IsoParser:
    """Backwards-compatible namespace for ISO parsing helpers."""

    parse_timestamp = staticmethod(parse_timestamp)
    parse_date = staticmethod(parse_date)
