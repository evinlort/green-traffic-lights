from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from db import db
from models import ClickEvent

bp = Blueprint("routes", __name__)


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
    speed: Optional[float]
    if speed_raw is None:
        speed = None
    else:
        try:
            speed = float(speed_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid data format"}), 400

    timestamp_raw = data.get("timestamp")
    if not isinstance(timestamp_raw, str):
        return jsonify({"error": "Invalid data format"}), 400

    try:
        timestamp_clean = timestamp_raw.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(timestamp_clean)
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone aware")
        timestamp = timestamp.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid data format"}), 400

    save_click_to_db(lat, lon, speed, timestamp)

    return jsonify({"status": "ok"}), 200
