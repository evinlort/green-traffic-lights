from __future__ import annotations

from sqlalchemy import Enum, func

from ..extensions import db


class TrafficLightPass(db.Model):
    __tablename__ = "traffic_light_pass"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    click_event_id = db.Column(db.Integer, db.ForeignKey("click_event.id"), nullable=False)
    light_identifier = db.Column(db.String(64), nullable=False)
    pass_color = db.Column(Enum("green", "red", name="traffic_light_pass_color"), nullable=False)
    speed_profile = db.Column(db.JSON, nullable=True)
    pass_timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    click_event = db.relationship("ClickEvent", backref="traffic_light_passes")
