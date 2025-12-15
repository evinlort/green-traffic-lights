from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional

from flask import Response, current_app, jsonify

from .traffic_lights import _get_traffic_lights_path


def load_traffic_light_payload() -> List[Any]:
    traffic_lights_file = _get_traffic_lights_path()

    try:
        raw_text = traffic_lights_file.read_text(encoding="utf-8")
        raw_data = json.loads(raw_text)
        if not isinstance(raw_data, list):
            current_app.logger.warning(
                "Traffic lights file does not contain a list: %s", traffic_lights_file
            )
            raw_data = []
    except FileNotFoundError:
        current_app.logger.warning(
            "Traffic lights file not found for client: %s", traffic_lights_file
        )
        raw_data = []
    except json.JSONDecodeError:
        current_app.logger.warning(
            "Traffic lights file contains invalid JSON for client: %s",
            traffic_lights_file,
        )
        raw_data = []
    except OSError:
        current_app.logger.exception(
            "Failed to read traffic lights file for client: %s", traffic_lights_file
        )
        raw_data = []

    return raw_data


def build_traffic_light_response(
    raw_data: Iterable[Any],
    *,
    no_store: bool = True,
    no_cache: bool = True,
    max_age: Optional[int] = 0,
) -> Response:
    response = jsonify(list(raw_data))
    response.cache_control.no_store = no_store
    response.cache_control.no_cache = no_cache
    response.cache_control.max_age = max_age
    return response
