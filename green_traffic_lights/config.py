from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Default configuration for the traffic lights application."""

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    _DEFAULT_DB_PATH = _PROJECT_ROOT / "greenlights.db"

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=30)

    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    TRAFFIC_LIGHTS_FILE = os.getenv("TRAFFIC_LIGHTS_FILE") or (_PROJECT_ROOT / "light_traffics.json")
    TRAFFIC_LIGHT_MAX_DISTANCE_METERS = os.getenv("TRAFFIC_LIGHT_MAX_DISTANCE_METERS")
