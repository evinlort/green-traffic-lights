from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_FOLDER = PROJECT_ROOT / "static"
_DEFAULT_DB_PATH = PROJECT_ROOT / "greenlights.db"
_DEFAULT_TRAFFIC_LIGHTS_FILE = PROJECT_ROOT / "light_traffics.json"


class Config:
    """Default configuration for the traffic lights application."""

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=30)

    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    TRAFFIC_LIGHTS_FILE = Path(os.getenv("TRAFFIC_LIGHTS_FILE", _DEFAULT_TRAFFIC_LIGHTS_FILE))

    _distance_raw = os.getenv("TRAFFIC_LIGHT_MAX_DISTANCE_METERS")
    try:
        TRAFFIC_LIGHT_MAX_DISTANCE_METERS = (
            float(_distance_raw) if _distance_raw is not None else None
        )
    except ValueError:
        TRAFFIC_LIGHT_MAX_DISTANCE_METERS = None
