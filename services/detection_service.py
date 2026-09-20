"""
Detection service orchestrating file storage, validation, and detector execution.
"""

import os
import uuid
from typing import Dict
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models.detector import predict_image, predict_video
from utils.preprocessing import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_IMAGE_SIZE_BYTES,
    MAX_VIDEO_SIZE_BYTES,
    get_file_extension,
    is_allowed_file,
)


class DetectionServiceError(Exception):
    """Base service exception with HTTP status code."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidFileTypeError(DetectionServiceError):
    def __init__(self, message: str = "Invalid file type."):
        super().__init__(message, status_code=400)


class FileTooLargeError(DetectionServiceError):
    def __init__(self, message: str = "File size exceeds limit."):
        super().__init__(message, status_code=413)


class MediaDecodeError(DetectionServiceError):
    def __init__(self, message: str = "Unable to decode media content."):
        super().__init__(message, status_code=422)


def process_image_upload(file: FileStorage, upload_folder: str) -> Dict[str, object]:
    """
    Validate, save, and analyze an uploaded image.
    """
    if not file or not file.filename:
        raise InvalidFileTypeError("No file uploaded or file field missing.")

    ext = get_file_extension(file.filename)
    if not is_allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        allowed = ", ".join(sorted(list(ALLOWED_IMAGE_EXTENSIONS))).upper()
        raise InvalidFileTypeError(f"Unsupported image format. Allowed formats: {allowed}.")

    # Measure file size
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)

    if size_bytes > MAX_IMAGE_SIZE_BYTES:
        raise FileTooLargeError("File exceeds the maximum allowed image size of 15 MB.")

    os.makedirs(upload_folder, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    save_path = os.path.join(upload_folder, safe_name)
    file.save(save_path)

    try:
        result = predict_image(save_path)
        return result
    except ValueError as e:
        raise MediaDecodeError(str(e))


def process_video_upload(file: FileStorage, upload_folder: str) -> Dict[str, object]:
    """
    Validate, save, and analyze an uploaded video.
    """
    if not file or not file.filename:
        raise InvalidFileTypeError("No file uploaded or file field missing.")

    ext = get_file_extension(file.filename)
    if not is_allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        allowed = ", ".join(sorted(list(ALLOWED_VIDEO_EXTENSIONS))).upper()
        raise InvalidFileTypeError(f"Unsupported video format. Allowed formats: {allowed}.")

    # Measure file size
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)

    if size_bytes > MAX_VIDEO_SIZE_BYTES:
        raise FileTooLargeError("File exceeds the maximum allowed video size of 100 MB.")

    os.makedirs(upload_folder, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    save_path = os.path.join(upload_folder, safe_name)
    file.save(save_path)

    try:
        result = predict_video(save_path)
        return result
    except ValueError as e:
        raise MediaDecodeError(str(e))
