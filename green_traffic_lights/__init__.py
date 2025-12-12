from __future__ import annotations

from flask import Flask
from flask_compress import Compress

from .config import Config, STATIC_FOLDER
from .extensions import db
from .routes import bp as routes_bp


def create_app() -> Flask:
    """Application factory that wires extensions, config, and routes."""

    app = Flask(__name__, static_folder=str(STATIC_FOLDER), static_url_path="")
    app.config.from_object(Config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(routes_bp)
    Compress(app)

    return app
