from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index() -> object:
    """Serve the main PWA entry point from the static folder."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/click", methods=["POST"])
def api_click() -> object:
    """Placeholder API route for handling click events."""
    return jsonify({"status": "ok", "message": "Placeholder click endpoint"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
