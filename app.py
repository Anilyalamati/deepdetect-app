"""
DeepDetect backend entry point.

Local development:
    cd backend
    pip install -r requirements.txt
    python app.py

The API is then available at http://localhost:5000 -- the frontend's
config.js points its fetch() calls there by default (see
../config.js).

Production:
    gunicorn app:app --bind 0.0.0.0:$PORT

`python app.py` runs Flask's own development server, which prints its
own warning that it isn't meant for production; gunicorn (already
listed in requirements.txt, and declared for exactly this in the
included Procfile) is the production-appropriate way to run this app.
No code changes are needed to switch -- `app` below is a plain WSGI
app either way.

All of the settings below can be overridden with environment
variables, so the same code runs the same way locally and on a
hosting platform without editing this file:

    PORT                  -- port to bind to (default 5000)
    FLASK_DEBUG           -- "true" to enable Flask's debug mode (default
                             "false" -- the interactive debugger it turns
                             on lets visitors run arbitrary code if it's
                             ever reachable publicly, so this defaults to
                             off rather than needing to be manually
                             disabled for deployment)
    ALLOWED_ORIGIN        -- value for Access-Control-Allow-Origin
                             (default "*" -- fine for a demo, but worth
                             narrowing to your deployed frontend's exact
                             origin once you have one)
    UPLOAD_FOLDER         -- where uploaded files are saved (default
                             backend/uploads)
    MAX_CONTENT_LENGTH_BYTES -- blanket request-size cap enforced by
                             Flask itself (default 100 MB, matching the
                             video size cap already enforced again in
                             routes/detection.py)
"""

import os

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from routes.detection import detection_bp
from models.detector import preload_model

UPLOAD_FOLDER = os.environ.get(
    "UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
)
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_BYTES", 100 * 1024 * 1024))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    app.register_blueprint(detection_bp)

    # Preload deep learning model weights on server start
    preload_model()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(_e):
        # Without this, a request over MAX_CONTENT_LENGTH gets Flask's
        # default HTML error page instead of JSON -- inconsistent for a
        # JSON API. This catches it regardless of which endpoint (or
        # which of the two size caps) triggered it.
        return jsonify({"error": "Upload is too large."}), 413

    @app.after_request
    def add_cors_headers(response):
        # Hand-rolled CORS (no flask-cors dependency needed) so the
        # frontend, served from a different origin/port, can call this
        # API. A plain POST with multipart/form-data (what the frontend
        # sends) doesn't trigger a browser preflight, so this header
        # alone is enough -- no separate OPTIONS handler needed.
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.route("/", methods=["GET"])
    def index():
        return jsonify(
            {
                "status": "ok",
                "service": "DeepDetect API",
                "endpoints": ["/api/detect/image", "/api/detect/video"],
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
