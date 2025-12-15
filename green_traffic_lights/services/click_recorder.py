from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..api.inferred_pass import InferredPassData
from ..models import ClickEvent, TrafficLightPass


class ClickRecorder:
    """Persist click events and optional inferred passes."""

    def __init__(self, session: Session, logger) -> None:
        self._session = session
        self._logger = logger

    def save_click(
        self,
        lat: float,
        lon: float,
        speed: Optional[float],
        timestamp: datetime,
        inferred_pass: Optional[InferredPassData] = None,
    ) -> None:
        click_event = ClickEvent(lat=lat, lon=lon, speed=speed, timestamp=timestamp)
        self._session.add(click_event)

        if inferred_pass is not None:
            traffic_pass = TrafficLightPass(
                click_event=click_event,
                light_identifier=inferred_pass.light_identifier,
                pass_color=inferred_pass.pass_color,
                speed_profile=inferred_pass.speed_profile,
                pass_timestamp=inferred_pass.pass_timestamp,
            )
            self._session.add(traffic_pass)

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            self._logger.exception("Failed to persist click event")
            raise
