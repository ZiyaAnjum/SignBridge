"""Model inference engine and compatibility loader for SignBridge."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F

from app.ml.architecture import SignBridgeGRU

logger = logging.getLogger("signbridge.engine")

ML_SERVICE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_DIR = ML_SERVICE_DIR / "models"

EXPECTED_LAYOUT_VERSION = "v1-225"
EXPECTED_FPS = 15
EXPECTED_WINDOW_LENGTH = 30
EXPECTED_NORMALIZATION_VERSION = "v1-shoulder-aspect"


class ModelEngine:
    """Manages model loading, metadata compatibility validation, and thread-safe inference."""

    def __init__(self, models_dir: Path = DEFAULT_MODELS_DIR, device: str = "cpu"):
        self.models_dir = Path(models_dir)
        self.device = torch.device(device)
        self.model: Optional[SignBridgeGRU] = None
        self.classes: List[str] = []
        self.label_to_id: Dict[str, int] = {}
        self.id_to_label: Dict[int, str] = {}
        self.metadata: Dict[str, any] = {}
        self.model_loaded: bool = False
        self.reason: Optional[str] = None

        self.load_model()

    def load_model(self) -> bool:
        """Loads model weights and validates compatibility metadata.
        
        Returns True if model was loaded and is ready for inference.
        """
        model_path = self.models_dir / "signbridge_gru.pt"
        label_map_path = self.models_dir / "label_map.json"

        if not model_path.exists() or not label_map_path.exists():
            self.model_loaded = False
            self.reason = f"Model artifacts not found in {self.models_dir} (missing signbridge_gru.pt or label_map.json)"
            logger.warning(self.reason)
            return False

        try:
            with open(label_map_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as exc:
            self.model_loaded = False
            self.reason = f"Failed to parse label_map.json: {exc}"
            logger.error(self.reason)
            return False

        # Validate compatibility metadata
        layout = metadata.get("landmark_layout_version")
        fps = metadata.get("fps")
        window_len = metadata.get("window_length")
        norm_ver = metadata.get("normalization_version")

        mismatches = []
        if layout != EXPECTED_LAYOUT_VERSION:
            mismatches.append(f"landmark_layout_version expected '{EXPECTED_LAYOUT_VERSION}', got '{layout}'")
        if fps != EXPECTED_FPS:
            mismatches.append(f"fps expected {EXPECTED_FPS}, got {fps}")
        if window_len != EXPECTED_WINDOW_LENGTH:
            mismatches.append(f"window_length expected {EXPECTED_WINDOW_LENGTH}, got {window_len}")
        if norm_ver != EXPECTED_NORMALIZATION_VERSION:
            mismatches.append(f"normalization_version expected '{EXPECTED_NORMALIZATION_VERSION}', got '{norm_ver}'")

        if mismatches:
            self.model_loaded = False
            self.reason = f"Model metadata incompatible: {'; '.join(mismatches)}"
            logger.warning(self.reason)
            return False

        classes = metadata.get("classes", [])
        if not classes:
            self.model_loaded = False
            self.reason = "label_map.json contains empty 'classes' list"
            logger.warning(self.reason)
            return False

        try:
            model = SignBridgeGRU(
                num_classes=len(classes),
                input_size=metadata.get("input_size", 225),
                hidden_size=metadata.get("hidden_size", 64),
                num_layers=metadata.get("num_layers", 1),
                bidirectional=metadata.get("bidirectional", True),
                dropout=metadata.get("dropout", 0.2),
            ).to(self.device)

            state_dict = torch.load(model_path, map_location=self.device)
            model.load_state_dict(state_dict)
            model.eval()

            self.model = model
            self.classes = classes
            self.label_to_id = {c: i for i, c in enumerate(classes)}
            self.id_to_label = {i: c for i, c in enumerate(classes)}
            self.metadata = metadata
            self.model_loaded = True
            self.reason = None
            logger.info(f"Loaded SignBridgeGRU model ({len(classes)} classes) on {self.device}")
            return True

        except Exception as exc:
            self.model_loaded = False
            self.reason = f"Failed to load model weights: {exc}"
            logger.error(self.reason, exc_info=True)
            return False

    def predict(self, normalized_seq: np.ndarray) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Runs forward inference on a normalized sequence of shape (30, 225).
        
        Returns:
            (top_label, top_confidence, all_predictions_sorted)
        """
        if not self.model_loaded or self.model is None:
            raise RuntimeError(f"Model not loaded: {self.reason}")

        if normalized_seq.shape != (30, 225):
            raise ValueError(f"Expected shape (30, 225), got {normalized_seq.shape}")

        tensor = torch.from_numpy(normalized_seq.astype(np.float32)).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).cpu().numpy()[0]

        # Top prediction
        top_idx = int(np.argmax(probs))
        top_label = self.classes[top_idx]
        top_conf = float(probs[top_idx])

        # All sorted descending
        sorted_indices = np.argsort(-probs)
        all_sorted = [(self.classes[i], float(probs[i])) for i in sorted_indices]

        return top_label, top_conf, all_sorted


# Global engine instance and accessors
_global_engine: Optional[ModelEngine] = None


def get_engine() -> ModelEngine:
    """Returns the active global ModelEngine instance."""
    global _global_engine
    if _global_engine is None:
        _global_engine = ModelEngine()
    return _global_engine


def set_engine(new_engine: ModelEngine) -> None:
    """Replaces active ModelEngine instance (e.g. after training or for test injection)."""
    global _global_engine
    _global_engine = new_engine


# Backward-compatible reference
engine = get_engine()
