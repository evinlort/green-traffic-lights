from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import current_app

from ..extensions import db
from ..models import ClickEvent, TrafficLightPass
from ..api.inferred_pass import InferredPassData


class ClickRecorder:
    """Persist click events and optional inferred passes."""

    @staticmethod
    def save_click(
        lat: float,
        lon: float,
        speed: Optional[float],
        timestamp: datetime,
        inferred_pass: Optional[InferredPassData] = None,
    ) -> None:
        click_event = ClickEvent(lat=lat, lon=lon, speed=speed, timestamp=timestamp)
        db.session.add(click_event)

        if inferred_pass is not None:
            traffic_pass = TrafficLightPass(
                click_event=click_event,
                light_identifier=inferred_pass.light_identifier,
                pass_color=inferred_pass.pass_color,
                speed_profile=inferred_pass.speed_profile,
                pass_timestamp=inferred_pass.pass_timestamp,
            )
            db.session.add(traffic_pass)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed to persist click event")
            raise
