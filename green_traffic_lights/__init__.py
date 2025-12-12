from __future__ import annotations

from pathlib import Path

from flask import Flask
from flask_compress import Compress

from .config import Config
from .extensions import db
from .routes import bp as routes_bp


def create_app() -> Flask:
    """Application factory that wires extensions, config, and routes."""

    project_root = Path(__file__).resolve().parent.parent
    static_folder = project_root / "static"

    app = Flask(__name__, static_folder=str(static_folder), static_url_path="")
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(routes_bp)
    Compress(app)

    return app
