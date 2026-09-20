"""
Media preprocessing helpers for DeepDetect.

Provides file validation, image verification, and video frame extraction.
"""

import os
from typing import List, Optional, Set
import cv2
import numpy as np
from PIL import Image

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {"mp4", "avi", "mov", "mkv"}

MAX_IMAGE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
MAX_VIDEO_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB


def get_file_extension(filename: str) -> str:
    """Extract lowercase file extension without leading period."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def is_allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """Check if the filename has an allowed extension."""
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def validate_and_load_image(file_path: str) -> Optional[np.ndarray]:
    """
    Validate that file_path points to a valid image, returning BGR numpy array.
    Returns None if decoding fails or file is corrupt.
    """
    try:
        # Verify with PIL first to detect subtle corruption or format mismatch
        with Image.open(file_path) as img:
            img.verify()

        # Reopen with PIL to convert to RGB then BGR for OpenCV consistency
        with Image.open(file_path) as img:
            rgb = img.convert("RGB")
            arr = np.array(rgb)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            return bgr
    except Exception:
        # Fallback to cv2.imread if PIL verify had strict header issues
        try:
            mat = cv2.imread(file_path, cv2.IMREAD_COLOR)
            if mat is not None and mat.size > 0:
                return mat
        except Exception:
            pass
        return None


def extract_video_frames(video_path: str, max_frames: int = 10) -> List[np.ndarray]:
    """
    Extract evenly sampled frames from a video file.
    Returns a list of BGR numpy frame arrays.
    Raises ValueError if video cannot be opened or has no decodable frames.
    """
    if not os.path.exists(video_path):
        raise ValueError("Video file does not exist.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: List[np.ndarray] = []

    try:
        if total_frames <= 0:
            # Fallback: sequential read up to max_frames
            count = 0
            while len(frames) < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                # Sample every 5th frame if possible
                if count % 5 == 0:
                    frames.append(frame)
                count += 1
        else:
            # Pick evenly spaced frame indices
            indices = np.linspace(0, max(0, total_frames - 1), num=min(max_frames, max(1, total_frames)), dtype=int)
            indices = sorted(list(set(indices)))

            for frame_idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    frames.append(frame)
    finally:
        cap.release()

    if not frames:
        raise ValueError("No valid video frames could be decoded.")

    return frames
