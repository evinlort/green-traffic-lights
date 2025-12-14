from __future__ import annotations

from datetime import datetime

import click
from flask import Flask
from flask_compress import Compress

from .config import Config, STATIC_FOLDER
from .extensions import db
from .routes import bp as routes_bp
from .services.aggregation import aggregate_passes_for_day


def create_app() -> Flask:
    """Application factory that wires extensions, config, and routes."""

    app = Flask(__name__, static_folder=str(STATIC_FOLDER), static_url_path="")
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(routes_bp)
    Compress(app)

    @app.cli.command("aggregate-passes")
    @click.option(
        "--day",
        help="UTC date to aggregate in YYYY-MM-DD format (defaults to previous UTC day)",
    )
    def aggregate_passes(day: str | None) -> None:
        """Aggregate saved traffic light passes into per-light ranges for a day."""

        target_day = None
        if day:
            try:
                target_day = datetime.strptime(day, "%Y-%m-%d").date()
            except ValueError as exc:
                raise click.BadParameter("Expected YYYY-MM-DD format") from exc

        aggregate_passes_for_day(target_day)

    return app
