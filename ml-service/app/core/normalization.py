"""Canonical landmark normalization module for SignBridge.
Shared logic mirroring frontend/src/lib/normalization.ts.
Spec defined in docs/LANDMARKS.md.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np

# Landmark slice boundaries
POSE_START = 0
POSE_END = 99        # 33 * 3
LEFT_HAND_START = 99
LEFT_HAND_END = 162  # 21 * 3
RIGHT_HAND_START = 162
RIGHT_HAND_END = 225 # 21 * 3

LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12
MIN_SHOULDER_WIDTH = 0.05
DEFAULT_ASPECT_RATIO = 16.0 / 9.0


class Anchor:
    """Shoulder anchor for normalization."""
    def __init__(self, mx: float, my: float, mz: float, scale: float):
        self.mx = mx
        self.my = my
        self.mz = mz
        self.scale = scale


def is_hand_detected(slice_data: np.ndarray) -> bool:
    """Return True if at least one coordinate in the 63-dim hand slice is non-zero."""
    return bool(np.any(slice_data != 0.0))


def compute_shoulder_anchor(
    frame: np.ndarray,
    aspect_ratio: float,
    last_anchor: Optional[Anchor] = None,
) -> Tuple[Anchor, bool]:
    """Compute shoulder midpoint anchor and scale from pose landmarks 11 and 12.
    
    Returns (Anchor, was_valid_anchor).
    """
    # Left shoulder: pose landmark 11 -> indices 33, 34, 35
    ls_x = float(frame[LEFT_SHOULDER_IDX * 3])
    ls_y = float(frame[LEFT_SHOULDER_IDX * 3 + 1])
    ls_z = float(frame[LEFT_SHOULDER_IDX * 3 + 2])

    # Right shoulder: pose landmark 12 -> indices 36, 37, 38
    rs_x = float(frame[RIGHT_SHOULDER_IDX * 3])
    rs_y = float(frame[RIGHT_SHOULDER_IDX * 3 + 1])
    rs_z = float(frame[RIGHT_SHOULDER_IDX * 3 + 2])

    # Check if either shoulder is missing (exact zeros)
    ls_missing = (ls_x == 0.0 and ls_y == 0.0 and ls_z == 0.0)
    rs_missing = (rs_x == 0.0 and rs_y == 0.0 and rs_z == 0.0)

    if ls_missing or rs_missing:
        if last_anchor is not None:
            return last_anchor, False
        # Neutral fallback
        return Anchor(mx=0.5 * aspect_ratio, my=0.5, mz=0.0, scale=1.0), False

    # Apply aspect ratio correction to horizontal coordinate x
    ls_x_aspect = ls_x * aspect_ratio
    rs_x_aspect = rs_x * aspect_ratio

    dx = ls_x_aspect - rs_x_aspect
    dy = ls_y - rs_y
    dz = ls_z - rs_z
    scale = math.sqrt(dx * dx + dy * dy + dz * dz)

    # Check if shoulder width is degenerate / too small
    if scale < MIN_SHOULDER_WIDTH:
        if last_anchor is not None:
            return last_anchor, False
        return Anchor(mx=0.5 * aspect_ratio, my=0.5, mz=0.0, scale=1.0), False

    mx = (ls_x_aspect + rs_x_aspect) / 2.0
    my = (ls_y + rs_y) / 2.0
    mz = (ls_z + rs_z) / 2.0

    return Anchor(mx=mx, my=my, mz=mz, scale=scale), True


def normalize_frame(
    frame: np.ndarray,
    aspect_ratio: float = DEFAULT_ASPECT_RATIO,
    last_anchor: Optional[Anchor] = None,
) -> Tuple[np.ndarray, Anchor]:
    """Normalize a single 225-dim landmark frame.
    
    Guarantees:
    1. Undetected hands remain strictly 0.0.
    2. Missing/degenerate shoulders fall back to last_anchor or neutral anchor.
    3. Aspect-corrected Euclidean scaling.
    """
    frame_arr = np.array(frame, dtype=np.float32).copy()
    if frame_arr.shape != (225,):
        raise ValueError(f"Expected frame shape (225,), got {frame_arr.shape}")

    anchor, _ = compute_shoulder_anchor(frame_arr, aspect_ratio, last_anchor)
    out = np.zeros(225, dtype=np.float32)

    # 1. Normalize Pose landmarks (indices 0..98) for detected points
    for i in range(33):
        idx = i * 3
        x = frame_arr[idx]
        y = frame_arr[idx + 1]
        z = frame_arr[idx + 2]
        if x != 0.0 or y != 0.0 or z != 0.0:
            out[idx] = (x * aspect_ratio - anchor.mx) / anchor.scale
            out[idx + 1] = (y - anchor.my) / anchor.scale
            out[idx + 2] = (z - anchor.mz) / anchor.scale

    # 2. Normalize Left Hand (indices 99..161) ONLY if hand detected
    lh_slice = frame_arr[LEFT_HAND_START:LEFT_HAND_END]
    if is_hand_detected(lh_slice):
        for i in range(21):
            idx = LEFT_HAND_START + i * 3
            x = frame_arr[idx]
            y = frame_arr[idx + 1]
            z = frame_arr[idx + 2]
            out[idx] = (x * aspect_ratio - anchor.mx) / anchor.scale
            out[idx + 1] = (y - anchor.my) / anchor.scale
            out[idx + 2] = (z - anchor.mz) / anchor.scale
    # If not detected, stays 0.0 by default in `out`

    # 3. Normalize Right Hand (indices 162..224) ONLY if hand detected
    rh_slice = frame_arr[RIGHT_HAND_START:RIGHT_HAND_END]
    if is_hand_detected(rh_slice):
        for i in range(21):
            idx = RIGHT_HAND_START + i * 3
            x = frame_arr[idx]
            y = frame_arr[idx + 1]
            z = frame_arr[idx + 2]
            out[idx] = (x * aspect_ratio - anchor.mx) / anchor.scale
            out[idx + 1] = (y - anchor.my) / anchor.scale
            out[idx + 2] = (z - anchor.mz) / anchor.scale
    # If not detected, stays 0.0 by default in `out`

    return out, anchor


def normalize_sequence(
    sequence: np.ndarray,
    aspect_ratio: float = DEFAULT_ASPECT_RATIO,
) -> np.ndarray:
    """Normalize a 2D sequence of shape (30, 225).
    Maintains anchor continuity across frames.
    """
    seq_arr = np.array(sequence, dtype=np.float32)
    if seq_arr.ndim != 2 or seq_arr.shape[1] != 225:
        raise ValueError(f"Expected sequence shape (N, 225), got {seq_arr.shape}")

    normalized = np.zeros_like(seq_arr)
    anchor: Optional[Anchor] = None

    for t in range(seq_arr.shape[0]):
        norm_frame, anchor = normalize_frame(seq_arr[t], aspect_ratio, anchor)
        normalized[t] = norm_frame

    return normalized

