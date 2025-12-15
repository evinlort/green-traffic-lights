from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .errors import PayloadError
from .time_parsers import IsoParser, parse_timestamp


@dataclass
class InferredPassData:
    light_identifier: str
    pass_color: str
    speed_profile: Any
    pass_timestamp: datetime


class InferredPassError(PayloadError):
    """Validation error for inferred pass payloads."""


class InferredPassParser:
    """Transform raw inferred pass payloads into validated dataclasses."""

    @staticmethod
    def parse(data: Any) -> Optional[InferredPassData]:
        if data is None:
            return None

        if not isinstance(data, dict):
            raise InferredPassError("Invalid inferred_state payload")

        light_identifier_raw = data.get("light_id") or data.get("light_identifier") or data.get("light_number")
        light_identifier = str(light_identifier_raw).strip() if light_identifier_raw is not None else ""
        if not light_identifier:
            raise InferredPassError("Missing inferred light identifier")

        pass_color_raw = data.get("color")
        pass_color = str(pass_color_raw).strip().lower() if isinstance(pass_color_raw, str) else None
        if pass_color not in {"green", "red"}:
            raise InferredPassError("Invalid inferred pass color")

        speed_profile = data.get("speed_profile")
        if speed_profile is not None and not isinstance(speed_profile, (dict, list, float, int, str)):
            raise InferredPassError("Invalid speed_profile format")
        if speed_profile is not None:
            speed_profile = InferredPassParser._ensure_json_safe(speed_profile)

        pass_timestamp_raw = data.get("pass_timestamp") or data.get("timestamp")
        if not isinstance(pass_timestamp_raw, str):
            raise InferredPassError("Invalid inferred pass timestamp")

        parsed_timestamp = parse_timestamp(pass_timestamp_raw)
        if parsed_timestamp is None:
            raise InferredPassError("Invalid inferred pass timestamp")

        return InferredPassData(
            light_identifier=light_identifier,
            pass_color=pass_color,
            speed_profile=speed_profile,
            pass_timestamp=parsed_timestamp,
        )

    @staticmethod
    def _ensure_json_safe(value: Any) -> Any:
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise InferredPassError("Invalid speed_profile format") from exc
        return value
