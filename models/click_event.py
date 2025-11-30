from __future__ import annotations

from datetime import timezone

from sqlalchemy import func
from db import db


class ClickEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
