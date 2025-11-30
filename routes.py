from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Tuple

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from db import db
from models import ClickEvent

bp = Blueprint("routes", __name__)
TRAFFIC_LIGHTS_FILE = Path(__file__).with_name("light_traffics.json")
DEFAULT_DISTANCE_THRESHOLD_METERS = 75.0

_TRAFFIC_LIGHTS: list[Tuple[float, float]] = []
_TRAFFIC_LIGHTS_MTIME: Optional[float] = None


def _load_traffic_lights() -> list[Tuple[float, float]]:
    """Load traffic light coordinates from the JSON file.

    The results are cached in memory after the first read to avoid
    unnecessary disk access on subsequent requests.
    """

    global _TRAFFIC_LIGHTS, _TRAFFIC_LIGHTS_MTIME

    try:
        mtime = TRAFFIC_LIGHTS_FILE.stat().st_mtime

        if _TRAFFIC_LIGHTS and _TRAFFIC_LIGHTS_MTIME == mtime:
            return _TRAFFIC_LIGHTS

        raw_data = json.loads(TRAFFIC_LIGHTS_FILE.read_text(encoding="utf-8"))

    except FileNotFoundError:
        current_app.logger.error("Traffic lights file not found: %s", TRAFFIC_LIGHTS_FILE)
        return []
    except json.JSONDecodeError:
        current_app.logger.error("Traffic lights file contains invalid JSON: %s", TRAFFIC_LIGHTS_FILE)
        return []

    parsed: list[Tuple[float, float]] = []
    discarded = 0
    for entry in raw_data:
        try:
            lat = float(entry["lat"])
            lon = float(entry["lon"])
        except (KeyError, TypeError, ValueError):
            discarded += 1
            continue

        parsed.append((lat, lon))

    if discarded:
        current_app.logger.warning(
            "Discarded %d malformed traffic light entries from %s", discarded, TRAFFIC_LIGHTS_FILE
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
    except (TypeError, ValueError):
        current_app.logger.warning(
            "Invalid TRAFFIC_LIGHT_MAX_DISTANCE_METERS=%r, falling back to default", raw
        )
        return DEFAULT_DISTANCE_THRESHOLD_METERS

    if threshold < 0 or not math.isfinite(threshold):
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
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius_m * c


def _nearest_distance(lat: float, lon: float, lights: Iterable[Tuple[float, float]]) -> Optional[float]:
    """Return the distance in meters to the nearest traffic light."""

    min_distance: Optional[float] = None
    for target_lat, target_lon in lights:
        distance = _haversine_distance_meters(lat, lon, target_lat, target_lon)
        if min_distance is None or distance < min_distance:
            min_distance = distance

    return min_distance


def _validate_click_distance(lat: float, lon: float) -> Optional[Tuple[dict[str, Any], int]]:
    traffic_lights = _load_traffic_lights()
    if not traffic_lights:
        current_app.logger.warning(
            "Traffic lights data unavailable; allowing click without distance enforcement"
        )
        return None

    distance_threshold = _get_distance_threshold()
    nearest_distance = _nearest_distance(lat, lon, traffic_lights)

    if nearest_distance is None:
        current_app.logger.warning(
            "Traffic lights data empty; allowing click without distance enforcement"
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


def save_click_to_db(lat: float, lon: float, speed: Optional[float], timestamp: datetime) -> None:
    """Persist click data to the configured database."""

    click_event = ClickEvent(lat=lat, lon=lon, speed=speed, timestamp=timestamp)
    db.session.add(click_event)
    db.session.commit()


@bp.route("/")
def index() -> Any:
    """Serve the main PWA entry point from the static folder."""

    return send_from_directory(current_app.static_folder, "index.html")


@bp.route("/api/click", methods=["POST"])
def api_click() -> Any:
    """Handle click events from the PWA client."""

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Missing required fields"}), 400

    required_fields = ("lat", "lon", "timestamp")
    if any(field not in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid data format"}), 400

    speed_raw = data.get("speed")
    if speed_raw is not None:
        try:
            speed = float(speed_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid data format"}), 400
    else:
        speed = None

    if not isinstance(timestamp_raw := data.get("timestamp"), str):
        return jsonify({"error": "Invalid data format"}), 400

    try:
        timestamp_clean = timestamp_raw.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(timestamp_clean)
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone aware")
        timestamp = timestamp.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid data format"}), 400

    validation_result = _validate_click_distance(lat, lon)
    if validation_result is not None:
        payload, status = validation_result
        return jsonify(payload), status

    save_click_to_db(lat, lon, speed, timestamp)

    return jsonify({"status": "ok"}), 200
