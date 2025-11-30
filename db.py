from __future__ import annotations

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app: Flask) -> None:
    """Initialize the database extension and create tables."""

    db.init_app(app)
    with app.app_context():
        db.create_all()
