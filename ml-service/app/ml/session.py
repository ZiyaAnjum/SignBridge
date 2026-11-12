"""Per-connection inference session state and smoothing logic.
Zero shared global state across connections.
"""
from __future__ import annotations

import collections
import math
import time
from typing import Counter, Deque, List, Optional, Tuple

import numpy as np

from app.core.normalization import (
    LEFT_SHOULDER_IDX,
    RIGHT_SHOULDER_IDX,
    LEFT_HAND_START,
    LEFT_HAND_END,
    RIGHT_HAND_START,
    RIGHT_HAND_END,
    MIN_SHOULDER_WIDTH,
    is_hand_detected,
    normalize_sequence,
)
from app.core.translations import get_label_translations
from app.ml.engine import ModelEngine
from app.schemas.protocol import PredictionResult, TopGuess

MAX_MESSAGE_BYTES = 65536  # 64 KB limit
MAX_FRAMES_PER_SECOND = 45  # Rate limit: expected ~15 fps


class ConnectionSession:
    """Encapsulates the rolling 30-frame buffer and temporal smoothing for a single WebSocket connection."""

    def __init__(self):
        # Rolling 30-frame raw landmark buffer
        self.buffer: Deque[np.ndarray] = collections.deque(maxlen=30)
        # Recent prediction windows (maxlen 5) holding (label, confidence)
        self.recent_windows: Deque[Tuple[str, float]] = collections.deque(maxlen=5)
        # Consecutive emergency window count
        self.consecutive_emergency_count: int = 0
        # Word repetition suppression: last emitted non-idle word
        self.last_reported_word: Optional[str] = None
        # Monotonic frame counter
        self.frame_counter: int = 0
        # Rate limiting: timestamps of frames received
        self.frame_timestamps: Deque[float] = collections.deque(maxlen=60)
        # In-flight inference flag: guarantees single active inference per connection
        self.is_inferring: bool = False

    def clear(self) -> None:
        """Clears all buffers and smoothing state."""
        self.buffer.clear()
        self.recent_windows.clear()
        self.consecutive_emergency_count = 0
        self.last_reported_word = None
        self.frame_counter = 0
        self.frame_timestamps.clear()
        self.is_inferring = False

    def check_rate_limit(self) -> bool:
        """Returns True if frame rate exceeds MAX_FRAMES_PER_SECOND."""
        now = time.time()
        self.frame_timestamps.append(now)
        # Count frames in the last 1.0 second
        cutoff = now - 1.0
        recent_count = sum(1 for t in self.frame_timestamps if t >= cutoff)
        return recent_count > MAX_FRAMES_PER_SECOND

    def validate_frame(self, raw_landmarks: any) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """Validates incoming landmark frame: exactly 225 finite floats."""
        if not isinstance(raw_landmarks, (list, tuple, np.ndarray)):
            return False, "Landmarks must be a list of floats", None

        if len(raw_landmarks) != 225:
            return False, f"Expected 225 landmarks, received {len(raw_landmarks)}", None

        try:
            arr = np.array(raw_landmarks, dtype=np.float32)
        except (ValueError, TypeError) as exc:
            return False, f"Invalid float values: {exc}", None

        # Check finite
        if not np.all(np.isfinite(arr)):
            return False, "Landmarks contain NaN or Inf values", None

        return True, None, arr

    def push_frame(self, frame_arr: np.ndarray) -> None:
        """Appends validated frame to the rolling 30-frame buffer."""
        self.buffer.append(frame_arr)
        self.frame_counter += 1

    def should_run_inference(self) -> bool:
        """Inference runs every 3 frames once the buffer has 30 frames."""
        return len(self.buffer) == 30 and (self.frame_counter % 3 == 0)

    def get_normalized_sequence(self) -> np.ndarray:
        """Extracts and normalizes the 30-frame buffer."""
        raw_seq = np.array(self.buffer, dtype=np.float32)
        return normalize_sequence(raw_seq)

    def check_signer_presence(self) -> Tuple[bool, Optional[str]]:
        """Evaluates whether an active signer is visible in the current 30-frame window.
        
        Per design rules:
        - If shoulders are missing in most of the window (>15 frames), or
        - If no hand is detected for most of the window (>20 frames),
        do not run the model and return state 'no_signer'.
        """
        if len(self.buffer) < 30:
            return True, None

        missing_shoulder_count = 0
        missing_hand_count = 0

        for frame in self.buffer:
            # Check shoulder landmarks 11 & 12
            ls_x = float(frame[LEFT_SHOULDER_IDX * 3])
            ls_y = float(frame[LEFT_SHOULDER_IDX * 3 + 1])
            ls_z = float(frame[LEFT_SHOULDER_IDX * 3 + 2])

            rs_x = float(frame[RIGHT_SHOULDER_IDX * 3])
            rs_y = float(frame[RIGHT_SHOULDER_IDX * 3 + 1])
            rs_z = float(frame[RIGHT_SHOULDER_IDX * 3 + 2])

            ls_missing = (ls_x == 0.0 and ls_y == 0.0 and ls_z == 0.0)
            rs_missing = (rs_x == 0.0 and rs_y == 0.0 and rs_z == 0.0)
            shoulder_width = math.sqrt((ls_x - rs_x) ** 2 + (ls_y - rs_y) ** 2 + (ls_z - rs_z) ** 2)

            if ls_missing or rs_missing or (shoulder_width < MIN_SHOULDER_WIDTH):
                missing_shoulder_count += 1

            # Check hands
            left_detected = is_hand_detected(frame[LEFT_HAND_START:LEFT_HAND_END])
            right_detected = is_hand_detected(frame[RIGHT_HAND_START:RIGHT_HAND_END])
            if not left_detected and not right_detected:
                missing_hand_count += 1

        if missing_shoulder_count > 15:
            return False, "Step into the frame: shoulders not clearly detected."

        if missing_hand_count > 20:
            return False, "Step into the frame: hands not detected."

        return True, None

    def process_prediction(
        self,
        current_label: str,
        current_conf: float,
        all_sorted: List[Tuple[str, float]],
        latency_ms: float,
    ) -> PredictionResult:
        """Applies SignBridge smoothing, repetition suppression, and emergency rules."""
        # Top 2 candidate guesses
        top_guesses = [
            TopGuess(label=lbl, confidence=round(c, 4))
            for lbl, c in all_sorted[:2]
        ]

        # 1. Emergency rule: ONLY 'emergency' and 'ambulance' with conf >= 0.9 on 3 consecutive windows
        if current_label in ("emergency", "ambulance") and current_conf >= 0.90:
            self.consecutive_emergency_count += 1
        else:
            self.consecutive_emergency_count = 0

        is_emergency = (self.consecutive_emergency_count >= 3)

        # 2. Record this window in recent_windows (maxlen 5)
        self.recent_windows.append((current_label, current_conf))

        # 3. Smoothing rule: report a word only when it wins at least 3 of the last 5 windows AND confidence >= 0.8
        counts = Counter(lbl for lbl, _ in self.recent_windows)
        winning_label, win_count = counts.most_common(1)[0]

        # Confidence of the winning label in the recent windows
        winning_conf = max(conf for lbl, conf in self.recent_windows if lbl == winning_label)

        reported_label: Optional[str] = None

        if win_count >= 3 and winning_conf >= 0.80:
            if winning_label == "idle":
                # Idle wins -> report nothing; reset repetition suppression
                reported_label = None
                self.last_reported_word = None
            else:
                # Word wins -> check repetition suppression
                if winning_label == self.last_reported_word:
                    # Suppressed repeating same word until idle or different word appears
                    reported_label = None
                else:
                    reported_label = winning_label
                    self.last_reported_word = winning_label
        else:
            # Low confidence or insufficient consensus -> return low-confidence result with top 2 guesses
            reported_label = None
            # If current window strongly predicts idle, reset repetition
            if current_label == "idle" and current_conf >= 0.80:
                self.last_reported_word = None

        # Determine operational state
        if is_emergency:
            state = "emergency"
        elif reported_label is not None:
            state = "ready"
        elif current_conf < 0.80:
            state = "low_confidence"
        else:
            state = "ready"

        # Translations lookup
        translations = get_label_translations(reported_label)

        return PredictionResult(
            label=reported_label,
            english=translations.get("english"),
            hindi=translations.get("hindi"),
            kannada=translations.get("kannada"),
            confidence=round(current_conf, 4),
            is_emergency=is_emergency,
            top_guesses=top_guesses,
            model_loaded=True,
            state=state,
            inference_latency_ms=round(latency_ms, 2),
            reason=None,
        )

    def create_no_signer_result(
        self,
        reason: str,
        model_loaded: bool = True,
    ) -> PredictionResult:
        """Creates response when signer is not clearly detected in the frame."""
        return PredictionResult(
            label=None,
            english=None,
            hindi=None,
            kannada=None,
            confidence=0.0,
            is_emergency=False,
            top_guesses=[],
            model_loaded=model_loaded,
            state="no_signer",
            inference_latency_ms=0.0,
            reason=reason,
        )

    def create_fallback_result(
        self,
        reason: str,
        latency_ms: float = 0.0,
    ) -> PredictionResult:
        """Creates dummy / fallback response when model is not loaded or during initial buffer filling."""
        state = "buffering" if "Buffering" in reason else "not_loaded"
        return PredictionResult(
            label=None,
            english=None,
            hindi=None,
            kannada=None,
            confidence=0.0,
            is_emergency=False,
            top_guesses=[],
            model_loaded=False,
            state=state,
            inference_latency_ms=round(latency_ms, 2),
            reason=reason,
        )

