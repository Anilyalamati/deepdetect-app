"""
Re-export detector interface for backend.models.detector namespace.
"""

from models.detector import (
    MODEL_NAME,
    format_prediction_result,
    get_device,
    load_model,
    predict_image,
    predict_pil_image,
    predict_video,
    preload_model,
)

__all__ = [
    "MODEL_NAME",
    "format_prediction_result",
    "get_device",
    "load_model",
    "predict_image",
    "predict_pil_image",
    "predict_video",
    "preload_model",
]
