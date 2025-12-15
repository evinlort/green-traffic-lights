from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .errors import PayloadError
from .inferred_pass import InferredPassData, InferredPassError, InferredPassParser
from .time_parsers import IsoParser, parse_timestamp


@dataclass
class ClickPayload:
    lat: float
    lon: float
    timestamp: datetime
    speed: Optional[float]
    inferred_pass: Optional[InferredPassData]

    @classmethod
    def from_raw(cls, data: Any) -> "ClickPayload":
        if not isinstance(data, dict):
            raise PayloadError("Missing required fields")

        cls._require_fields(data, ("lat", "lon", "timestamp"))

        lat, lon = cls._parse_coordinates(data)
        speed = cls._parse_speed(data.get("speed"))
        timestamp = cls._parse_timestamp(data.get("timestamp"))

        try:
            inferred_pass = InferredPassParser.parse(data.get("inferred_state"))
        except InferredPassError as exc:
            raise PayloadError(exc.payload["error"], exc.status) from exc

        return cls(lat=lat, lon=lon, timestamp=timestamp, speed=speed, inferred_pass=inferred_pass)

    @staticmethod
    def _require_fields(data: dict[str, Any], required_fields: tuple[str, ...]) -> None:
        if any(field not in data for field in required_fields):
            raise PayloadError("Missing required fields")

    @staticmethod
    def _parse_coordinates(data: dict[str, Any]) -> tuple[float, float]:
        try:
            lat = float(data["lat"])
            lon = float(data["lon"])
        except (TypeError, ValueError):
            raise PayloadError("Invalid data format") from None

        if not (math.isfinite(lat) and math.isfinite(lon)):
            raise PayloadError("Invalid coordinates")

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise PayloadError("Invalid coordinates")

        return lat, lon

    @staticmethod
    def _parse_speed(speed_raw: Any) -> Optional[float]:
        if speed_raw is None:
            return None

        try:
            return float(speed_raw)
        except (TypeError, ValueError):
            raise PayloadError("Invalid data format") from None

    @staticmethod
    def _parse_timestamp(timestamp_raw: Any) -> datetime:
        if not isinstance(timestamp_raw, str):
            raise PayloadError("Invalid data format")

        parsed = parse_timestamp(timestamp_raw)
        if parsed is None:
            raise PayloadError("Invalid data format")

        return parsed
