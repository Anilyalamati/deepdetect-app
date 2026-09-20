"""
Detection Blueprint for DeepDetect.

Exposes:
  POST /api/detect/image
  POST /api/detect/video
"""

from flask import Blueprint, current_app, jsonify, request

from services.detection_service import (
    DetectionServiceError,
    process_image_upload,
    process_video_upload,
)

detection_bp = Blueprint("detection", __name__, url_prefix="/api/detect")


@detection_bp.route("/image", methods=["POST"])
def detect_image():
    """
    Handle image upload and forensic detection.
    Expects multipart/form-data with a 'file' field.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Expected 'file' multipart field."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No selected file provided."}), 400

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")

    try:
        result = process_image_upload(uploaded_file, upload_folder)
        return jsonify(result), 200
    except DetectionServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.exception("Unexpected error analyzing image: %s", e)
        return jsonify({"error": "An error occurred while analyzing the image."}), 500


@detection_bp.route("/video", methods=["POST"])
def detect_video():
    """
    Handle video upload and forensic detection.
    Expects multipart/form-data with a 'file' field.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Expected 'file' multipart field."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No selected file provided."}), 400

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")

    try:
        result = process_video_upload(uploaded_file, upload_folder)
        return jsonify(result), 200
    except DetectionServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        current_app.logger.exception("Unexpected error analyzing video: %s", e)
        return jsonify({"error": "An error occurred while analyzing the video."}), 500
