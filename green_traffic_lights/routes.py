from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from .extensions import db
from .models import ClickEvent
from .services.traffic_lights import _get_traffic_lights_path, validate_click_distance

bp = Blueprint("routes", __name__)
HTML_SUBDIR = "html"
STATIC_IMMUTABLE_EXTS = (
    ".css",
    ".js",
    ".json",
    ".png",
    ".svg",
    ".webp",
    ".ico",
    ".txt",
)


def save_click_to_db(lat: float, lon: float, speed: Optional[float], timestamp: datetime) -> None:
    """Persist click data to the configured database."""

    click_event = ClickEvent(lat=lat, lon=lon, speed=speed, timestamp=timestamp)
    db.session.add(click_event)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to persist click event")
        raise


def _get_html_dir() -> str:
    return str(Path(current_app.static_folder) / HTML_SUBDIR)


@bp.route("/")
@bp.route("/index.html")
def index() -> Any:
    """Serve the main PWA entry point from the static folder."""

    return send_from_directory(_get_html_dir(), "index.html")


@bp.route("/green_way")
@bp.route("/green_way.html")
def green_way() -> Any:
    """Serve the dedicated Green Way map view."""

    return send_from_directory(_get_html_dir(), "green_way.html")


@bp.route("/privacy.html")
def privacy_policy() -> Any:
    """Serve the privacy policy page."""

    return send_from_directory(_get_html_dir(), "privacy.html")


@bp.route("/light_traffics.json")
def light_traffics() -> Any:
    """Serve the traffic lights coordinates JSON to the client.

    The file is stored next to the Flask app (or at ``TRAFFIC_LIGHTS_FILE``) for
    server-side validation, so expose it via an explicit route instead of the
    static folder. When the file is missing or malformed, return an empty list
    to keep the client map usable.
    """

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

    response = jsonify(raw_data)
    response.cache_control.no_store = True
    response.cache_control.no_cache = True
    response.cache_control.max_age = 0
    return response


@bp.route("/maps-config.js")
def maps_config() -> Any:
    """Expose the Google Maps API key without persisting it in the static files."""

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY", "")
    payload = f"window.GOOGLE_MAPS_API_KEY = {json.dumps(api_key)};\n"

    response = current_app.response_class(payload, mimetype="application/javascript")
    response.cache_control.no_store = True
    response.cache_control.max_age = 0
    return response


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

    if not (math.isfinite(lat) and math.isfinite(lon)):
        return jsonify({"error": "Invalid coordinates"}), 400

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return jsonify({"error": "Invalid coordinates"}), 400

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

    validation_result = validate_click_distance(lat, lon)
    if validation_result is not None:
        payload, status = validation_result
        return jsonify(payload), status

    save_click_to_db(lat, lon, speed, timestamp)

    return jsonify({"status": "ok"}), 200


@bp.after_request
def add_cache_headers(response: Any) -> Any:
    """Add cache headers to speed up static asset delivery."""

    if request.method != "GET":
        return response

    path = request.path
    if path == "/" or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    elif any(path.endswith(ext) for ext in STATIC_IMMUTABLE_EXTS):
        response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")

    return response
