from __future__ import annotations

from green_traffic_lights import create_app


app = create_app()


if __name__ == "__main__":
    # Use adhoc TLS so HTTPS requests do not fail with "Bad request version".
    app.run(host="0.0.0.0", port=8000, debug=True, ssl_context="adhoc")
