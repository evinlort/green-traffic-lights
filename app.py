from __future__ import annotations

import os
from datetime import timedelta

from flask import Flask
from flask_compress import Compress

from db import init_db
from routes import bp as routes_bp

app = Flask(__name__, static_folder="static", static_url_path="")
_default_db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "greenlights.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=30)

init_db(app)
app.register_blueprint(routes_bp)
Compress(app)


if __name__ == "__main__":
    # Use adhoc TLS so HTTPS requests do not fail with "Bad request version".
    app.run(host="0.0.0.0", port=8000, debug=True, ssl_context="adhoc")
