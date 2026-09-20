"""
DeepDetect AI Detector Model Module.

Integrates a pretrained Vision Transformer (ViT) deep learning model from
Hugging Face ('umm-maybe/AI-image-detector') to classify images and video frames
as either AI-generated ('artificial' / deepfake) or real ('human').

Features:
- Preloaded model weights on application startup for low-latency inference.
- GPU acceleration if available, falling back seamlessly to CPU.
- Standardized, normalized probabilities for `real_probability` and `deepfake_probability`.
- Support for still images and sampled video clips.
"""

import os
from typing import Dict, List, Optional
import cv2
import numpy as np
from PIL import Image
import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

from utils.preprocessing import extract_video_frames

MODEL_NAME = os.environ.get("DEEPDETECT_MODEL_NAME", "umm-maybe/AI-image-detector")

_processor: Optional[AutoImageProcessor] = None
_model: Optional[AutoModelForImageClassification] = None
_device: Optional[torch.device] = None
_fake_idx: int = 0
_real_idx: int = 1


def get_device() -> torch.device:
    """Determine optimal compute device (CUDA GPU or CPU)."""
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def load_model():
    """
    Load and cache the pretrained Hugging Face model and image processor.
    Identifies class index mapping for artificial (deepfake) vs human (real).
    """
    global _processor, _model, _fake_idx, _real_idx
    if _model is not None and _processor is not None:
        return _processor, _model

    device = get_device()
    print(f"[DeepDetect] Loading pretrained model '{MODEL_NAME}' onto {device}...")

    _processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    _model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)
    _model.to(device)
    _model.eval()

    # Determine index mapping from id2label
    id2label = _model.config.id2label or {0: "artificial", 1: "human"}
    for idx_key, label in id2label.items():
        idx = int(idx_key)
        lbl_lower = str(label).lower()
        if any(term in lbl_lower for term in ["artificial", "fake", "deepfake", "synthetic", "ai"]):
            _fake_idx = idx
        elif any(term in lbl_lower for term in ["human", "real", "authentic"]):
            _real_idx = idx

    print(f"[DeepDetect] Model loaded successfully. Index mapping: fake={_fake_idx}, real={_real_idx} ({id2label})")
    return _processor, _model


def preload_model():
    """Explicit hook to preload weights during server bootstrap."""
    load_model()


def format_prediction_result(deepfake_prob: float, real_prob: float, media_type: str = "image") -> Dict[str, object]:
    """
    Format output with normalized probabilities, confidence score, and descriptive message.
    """
    # Normalize probabilities to strictly sum to 1.0
    total = deepfake_prob + real_prob
    if total > 0:
        norm_fake = deepfake_prob / total
        norm_real = real_prob / total
    else:
        norm_fake = 0.5
        norm_real = 0.5

    # Clamp to avoid extreme 0% or 100% rounding
    norm_fake = min(0.999, max(0.001, norm_fake))
    norm_real = min(0.999, max(0.001, norm_real))

    deepfake_probability = round(norm_fake, 4)
    real_probability = round(1.0 - deepfake_probability, 4)

    is_deepfake = deepfake_probability >= 0.50
    prediction = "deepfake" if is_deepfake else "real"
    confidence = deepfake_probability if is_deepfake else real_probability

    if is_deepfake:
        confidence_pct = confidence * 100
        message = (
            f"Pretrained Vision Transformer detected AI synthesis artifacts with "
            f"{confidence_pct:.1f}% confidence in the analyzed {media_type}."
        )
    else:
        confidence_pct = confidence * 100
        message = (
            f"Pretrained Vision Transformer evaluated the {media_type} as authentic/human "
            f"with {confidence_pct:.1f}% confidence."
        )

    return {
        "prediction": prediction,
        "confidence": confidence,
        "real_probability": real_probability,
        "deepfake_probability": deepfake_probability,
        "message": message,
    }


def predict_pil_image(image: Image.Image) -> Dict[str, float]:
    """Run model inference on a PIL RGB image."""
    processor, model = load_model()
    device = get_device()

    rgb_image = image.convert("RGB")
    inputs = processor(images=rgb_image, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

    fake_p = float(probs[_fake_idx].item())
    real_p = float(probs[_real_idx].item())
    return {"deepfake_prob": fake_p, "real_prob": real_p}


def predict_image(image_path: str) -> Dict[str, object]:
    """
    Perform deep learning deepfake detection on an uploaded image file.
    Raises ValueError if image decoding fails.
    """
    if not os.path.exists(image_path):
        raise ValueError("Image file not found.")

    try:
        with Image.open(image_path) as img:
            img.load()
            res = predict_pil_image(img)
            return format_prediction_result(
                deepfake_prob=res["deepfake_prob"],
                real_prob=res["real_prob"],
                media_type="image",
            )
    except Exception as e:
        raise ValueError(f"Could not decode image content: {e}")


def predict_video(video_path: str, sample_frames: int = 8) -> Dict[str, object]:
    """
    Perform deep learning deepfake detection on sampled video frames.
    Extracts evenly spaced frames and aggregates frame-level predictions.
    Raises ValueError if video decoding fails or no frames found.
    """
    frames = extract_video_frames(video_path, max_frames=sample_frames)
    if not frames:
        raise ValueError("Could not extract any decodable frames from video.")

    fake_scores: List[float] = []
    real_scores: List[float] = []

    for frame_bgr in frames:
        # Convert BGR frame from OpenCV to RGB PIL Image
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        res = predict_pil_image(pil_img)
        fake_scores.append(res["deepfake_prob"])
        real_scores.append(res["real_prob"])

    # Aggregate across frames: mean of predictions
    avg_fake = float(np.mean(fake_scores))
    avg_real = float(np.mean(real_scores))

    return format_prediction_result(
        deepfake_prob=avg_fake,
        real_prob=avg_real,
        media_type="video",
    )
