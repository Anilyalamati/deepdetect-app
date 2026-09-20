"""
API and backend test suite for DeepDetect.
Tests Flask endpoints, request validation, error status codes, and CORS headers.
"""

import io
import os
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import cv2
import numpy as np
from PIL import Image

from app import create_app


def create_test_image_bytes(format="JPEG", width=100, height=100, color=(120, 80, 200)) -> bytes:
    """Generate in-memory image bytes for testing."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def create_test_video_bytes(num_frames=5, width=64, height=64) -> bytes:
    """Generate in-memory video bytes using cv2.VideoWriter and temporary file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(tmp_path, fourcc, 10.0, (width, height))
        for i in range(num_frames):
            frame = np.full((height, width, 3), (i * 40) % 255, dtype=np.uint8)
            out.write(frame)
        out.release()

        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


class TestDeepDetectAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_upload_dir = tempfile.mkdtemp()
        os.environ["UPLOAD_FOLDER"] = cls.temp_upload_dir
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_health_check_endpoint(self):
        """GET / should return 200 with service info and endpoints."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "DeepDetect API")
        self.assertIn("/api/detect/image", data.get("endpoints", []))
        self.assertIn("/api/detect/video", data.get("endpoints", []))

    def test_cors_headers(self):
        """API should return CORS headers matching app configuration."""
        res = self.client.get("/")
        self.assertIn("Access-Control-Allow-Origin", res.headers)
        self.assertEqual(res.headers["Access-Control-Allow-Origin"], "*")

    def test_detect_image_valid(self):
        """POST /api/detect/image with valid JPG should return 200 and detection payload."""
        img_bytes = create_test_image_bytes(format="JPEG")
        data = {
            "file": (io.BytesIO(img_bytes), "sample.jpg", "image/jpeg")
        }
        res = self.client.post("/api/detect/image", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()

        self.assertIn(payload.get("prediction"), ["deepfake", "real"])
        self.assertIsInstance(payload.get("confidence"), float)
        self.assertIsInstance(payload.get("real_probability"), float)
        self.assertIsInstance(payload.get("deepfake_probability"), float)
        self.assertIsInstance(payload.get("message"), str)
        self.assertAlmostEqual(payload["real_probability"] + payload["deepfake_probability"], 1.0, places=2)

    def test_detect_image_missing_file(self):
        """POST /api/detect/image without file should return 400."""
        res = self.client.post("/api/detect/image", data={}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        payload = res.get_json()
        self.assertIn("error", payload)

    def test_detect_image_invalid_extension(self):
        """POST /api/detect/image with disallowed extension should return 400."""
        data = {
            "file": (io.BytesIO(b"dummy text content"), "sample.txt", "text/plain")
        }
        res = self.client.post("/api/detect/image", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        payload = res.get_json()
        self.assertIn("error", payload)
        self.assertIn("Unsupported", payload["error"])

    def test_detect_image_corrupt_content(self):
        """POST /api/detect/image with invalid/corrupt image bytes should return 422."""
        data = {
            "file": (io.BytesIO(b"this is not a valid jpeg or png file header"), "corrupt.jpg", "image/jpeg")
        }
        res = self.client.post("/api/detect/image", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 422)
        payload = res.get_json()
        self.assertIn("error", payload)

    def test_detect_image_oversized(self):
        """POST /api/detect/image exceeding 15MB size limit should return 413."""
        # 16 MB dummy payload
        big_bytes = b"0" * (16 * 1024 * 1024)
        data = {
            "file": (io.BytesIO(big_bytes), "huge.jpg", "image/jpeg")
        }
        res = self.client.post("/api/detect/image", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 413)
        payload = res.get_json()
        self.assertIn("error", payload)

    def test_detect_video_valid(self):
        """POST /api/detect/video with valid mp4 should return 200 and detection payload."""
        vid_bytes = create_test_video_bytes(num_frames=4)
        data = {
            "file": (io.BytesIO(vid_bytes), "clip.mp4", "video/mp4")
        }
        res = self.client.post("/api/detect/video", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()

        self.assertIn(payload.get("prediction"), ["deepfake", "real"])
        self.assertIsInstance(payload.get("confidence"), float)
        self.assertIsInstance(payload.get("real_probability"), float)
        self.assertIsInstance(payload.get("deepfake_probability"), float)
        self.assertIsInstance(payload.get("message"), str)

    def test_detect_video_missing_file(self):
        """POST /api/detect/video without file should return 400."""
        res = self.client.post("/api/detect/video", data={}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        payload = res.get_json()
        self.assertIn("error", payload)

    def test_detect_video_invalid_extension(self):
        """POST /api/detect/video with .exe extension should return 400."""
        data = {
            "file": (io.BytesIO(b"data"), "payload.exe", "application/octet-stream")
        }
        res = self.client.post("/api/detect/video", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        payload = res.get_json()
        self.assertIn("error", payload)

    def test_detect_video_corrupt_content(self):
        """POST /api/detect/video with unreadable video content should return 422."""
        data = {
            "file": (io.BytesIO(b"garbage video stream bytes"), "damaged.mp4", "video/mp4")
        }
        res = self.client.post("/api/detect/video", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 422)
        payload = res.get_json()
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
