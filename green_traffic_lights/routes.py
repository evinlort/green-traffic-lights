from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from .api.click_payload import ClickPayload
from .api.errors import PayloadError
from .api.time_parsers import parse_date
from .extensions import db
from .services.aggregation import get_ranges_for_light
from .services.click_recorder import ClickRecorder
from .services.traffic_light_assets import (
    build_traffic_light_response,
    load_traffic_light_payload,
)
from .services.traffic_lights import validate_click_distance

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


def _get_html_dir() -> str:
    return str(Path(current_app.static_folder) / HTML_SUBDIR)


@bp.route("/")
@bp.route("/index.html")
def index() -> Any:
    """Serve the main PWA entry point from the static folder."""

    return send_from_directory(_get_html_dir(), "green_way.html")


@bp.route("/green_way")
@bp.route("/green_way.html")
def green_way() -> Any:
    """Serve the dedicated Green Way map view."""

    return send_from_directory(_get_html_dir(), "green_way.html")


@bp.route("/green_light")
@bp.route("/green_light.html")
def green_light() -> Any:
    """Serve the classic Green Light button interface."""

    return send_from_directory(_get_html_dir(), "green_light.html")


@bp.route("/privacy.html")
def privacy_policy() -> Any:
    """Serve the privacy policy page."""

    return send_from_directory(_get_html_dir(), "privacy.html")


@bp.route("/light_traffics.json")
def light_traffics() -> Any:
    """Serve the traffic lights coordinates JSON to the client."""

    raw_data = load_traffic_light_payload()
    return build_traffic_light_response(raw_data)


@bp.route("/api/lights/<light_identifier>/ranges", methods=["GET"])
def api_light_ranges(light_identifier: str) -> Any:
    """Expose aggregated red/green ranges for a traffic light.

    Query params:
    - ``day`` (optional): UTC date in ``YYYY-MM-DD`` format; defaults to the
      previous UTC day if omitted to mirror aggregation defaults.
    """

    day_param = request.args.get("day")
    target_day: Optional[date] = None

    if day_param:
        parsed_day = parse_date(day_param)
        if parsed_day is None:
            return jsonify({"error": "Invalid day format; expected YYYY-MM-DD"}), 400
        target_day = parsed_day

    normalized_light_identifier = light_identifier.strip()
    ranges = get_ranges_for_light(normalized_light_identifier, target_day)

    payload = [
        {
            "light_identifier": range_.light_identifier,
            "color": range_.color,
            "start_time": range_.start_time.isoformat(),
            "end_time": range_.end_time.isoformat(),
            "day": range_.day.isoformat(),
        }
        for range_ in ranges
    ]

    return jsonify({"light_identifier": normalized_light_identifier, "ranges": payload})


@bp.route("/maps-config.js")
def maps_config() -> Any:
    """Expose the Google Maps API key without persisting it in the static files."""

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY", "")
    payload = f"window.GOOGLE_MAPS_API_KEY = {json.dumps(api_key)};\n"

    response = current_app.response_class(payload, mimetype="application/javascript")
    response.cache_control.no_store = True
    response.cache_control.max_age = 0
    return response


@bp.route("/api/green_light", methods=["POST"])
def api_green_light() -> Any:
    """Handle green light click events from the PWA client."""

    try:
        payload = ClickPayload.from_raw(request.get_json(silent=True))
    except PayloadError as exc:
        return jsonify(exc.payload), exc.status

    validation_result = validate_click_distance(payload.lat, payload.lon)
    if validation_result is not None:
        validation_payload, status = validation_result
        return jsonify(validation_payload), status

    ClickRecorder(db.session, current_app.logger).save_click(
        payload.lat,
        payload.lon,
        payload.speed,
        payload.timestamp,
        payload.inferred_pass,
    )

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
