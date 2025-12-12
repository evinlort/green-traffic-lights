from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

from flask import current_app

DEFAULT_TRAFFIC_LIGHTS_FILENAME = "light_traffics.json"
# Default to a 50 m radius to filter out only the nearest, directly visible lights
# while still allowing legitimate remote activations.
DEFAULT_DISTANCE_THRESHOLD_METERS = 50.0

_TRAFFIC_LIGHTS: list[Tuple[float, float]] = []
_TRAFFIC_LIGHTS_MTIME: Optional[float] = None
_TRAFFIC_LIGHTS_PATH: Optional[Path] = None


def _get_traffic_lights_path() -> Path:
    """Return an absolute path to the traffic lights JSON file.

    The path is configurable via ``TRAFFIC_LIGHTS_FILE``; relative paths are
    treated as being rooted at ``current_app.root_path``. When not configured,
    the default ``light_traffics.json`` next to the Flask app is used.
    """

    configured = current_app.config.get("TRAFFIC_LIGHTS_FILE")

    if configured:
        configured_path = Path(configured)
        if not configured_path.is_absolute():
            configured_path = Path(current_app.root_path) / configured_path
        return configured_path

    return Path(current_app.root_path) / DEFAULT_TRAFFIC_LIGHTS_FILENAME


def _load_traffic_lights() -> list[Tuple[float, float]]:
    """Load traffic light coordinates from the JSON file with mtime caching."""

    global _TRAFFIC_LIGHTS, _TRAFFIC_LIGHTS_MTIME, _TRAFFIC_LIGHTS_PATH

    traffic_lights_file = _get_traffic_lights_path()

    if _TRAFFIC_LIGHTS_PATH != traffic_lights_file:
        _TRAFFIC_LIGHTS = []
        _TRAFFIC_LIGHTS_MTIME = None
        _TRAFFIC_LIGHTS_PATH = traffic_lights_file

    try:
        mtime = traffic_lights_file.stat().st_mtime

        if _TRAFFIC_LIGHTS and _TRAFFIC_LIGHTS_MTIME == mtime:
            return _TRAFFIC_LIGHTS

        raw_data = json.loads(traffic_lights_file.read_text(encoding="utf-8"))

    except FileNotFoundError:
        if _TRAFFIC_LIGHTS:
            current_app.logger.warning(
                "Traffic lights file missing; using cached data from previous load"
            )
            return _TRAFFIC_LIGHTS

        current_app.logger.error("Traffic lights file not found: %s", traffic_lights_file)
        return []
    except json.JSONDecodeError:
        current_app.logger.error(
            "Traffic lights file contains invalid JSON: %s", traffic_lights_file
        )
        if _TRAFFIC_LIGHTS:
            _TRAFFIC_LIGHTS_MTIME = mtime
            current_app.logger.warning(
                "Using cached traffic lights; latest file is malformed"
            )
            return _TRAFFIC_LIGHTS
        return []

    if not isinstance(raw_data, list):
        current_app.logger.warning(
            "Unexpected traffic lights data type %s; expected a list of entries", type(raw_data).__name__
        )
        return []

    parsed: list[Tuple[float, float]] = []
    discarded = 0
    for entry in raw_data:
        if not isinstance(entry, dict):
            discarded += 1
            continue
        try:
            lat = float(entry["lat"])
            lon = float(entry["lon"])
        except (KeyError, TypeError, ValueError):
            discarded += 1
            continue

        parsed.append((lat, lon))

    if discarded:
        current_app.logger.warning(
            "Discarded %d malformed traffic light entries from %s", discarded, traffic_lights_file
        )

    _TRAFFIC_LIGHTS = parsed
    _TRAFFIC_LIGHTS_MTIME = mtime

    return _TRAFFIC_LIGHTS


def _get_distance_threshold() -> float:
    """Return a validated distance threshold value in meters."""

    raw = current_app.config.get(
        "TRAFFIC_LIGHT_MAX_DISTANCE_METERS", DEFAULT_DISTANCE_THRESHOLD_METERS
    )

    try:
        threshold = float(raw)
        if threshold < 0 or not math.isfinite(threshold):
            raise ValueError
    except (TypeError, ValueError):
        current_app.logger.warning(
            "Invalid TRAFFIC_LIGHT_MAX_DISTANCE_METERS=%r, falling back to default", raw
        )
        return DEFAULT_DISTANCE_THRESHOLD_METERS

    return threshold


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance between two coordinates in meters."""

    radius_m = 6_371_000  # Earth radius in meters

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    # Numerical imprecision can push "a" slightly outside the valid [0, 1] range,
    # causing a domain error in the square root when subtracting from 1. Clamp to
    # the expected bounds to keep the calculation stable.
    a = min(1.0, max(0.0, a))

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius_m * c


def _nearest_distance(lat: float, lon: float, lights: Iterable[Tuple[float, float]]) -> Optional[float]:
    """Return the distance in meters to the nearest traffic light."""

    return min(
        (
            _haversine_distance_meters(lat, lon, target_lat, target_lon)
            for target_lat, target_lon in lights
        ),
        default=None,
    )


def validate_click_distance(lat: float, lon: float) -> Optional[Tuple[dict[str, Any], int]]:
    traffic_lights = _load_traffic_lights()
    distance_threshold = _get_distance_threshold()
    nearest_distance = _nearest_distance(lat, lon, traffic_lights)

    if nearest_distance is None:
        current_app.logger.warning(
            "Traffic lights data unavailable or empty; allowing click without distance enforcement"
        )
        return None

    if nearest_distance > distance_threshold:
        return (
            {
                "error": "Вы находитесь слишком далеко от ближайшего светофора для отправки сигнала.",
                "details": {"distance_m": round(nearest_distance, 1)},
            },
            400,
        )

    return None
