from __future__ import annotations

from sqlalchemy import Enum, func

from ..extensions import db


class TrafficLightRange(db.Model):
    __tablename__ = "traffic_light_range"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    light_identifier = db.Column(db.String(64), nullable=False)
    color = db.Column(Enum("green", "red", name="traffic_light_range_color"), nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    day = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
