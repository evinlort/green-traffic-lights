from __future__ import annotations

import json
from typing import Any, List

from flask import current_app, jsonify

from .traffic_lights import _get_traffic_lights_path


class TrafficLightAssetLoader:
    """Load traffic light definitions for client consumption."""

    @staticmethod
    def load_json_payload() -> List[Any]:
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
                "Traffic lights file contains invalid JSON for client: %s", traffic_lights_file
            )
            raw_data = []
        except OSError:
            current_app.logger.exception(
                "Failed to read traffic lights file for client: %s", traffic_lights_file
            )
            raw_data = []

        return raw_data

    @staticmethod
    def make_response(raw_data: List[Any]):
        response = jsonify(raw_data)
        response.cache_control.no_store = True
        response.cache_control.no_cache = True
        response.cache_control.max_age = 0
        return response
