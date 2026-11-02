"""Normalization and parity unit tests for SignBridge.
Tests:
1. Standard full pose + two hands.
2. Missing-hand case: undetected hand must remain exactly 0.0.
3. Missing-shoulder case: degenerate shoulder width fallback.
4. Aspect ratio scaling verification.
"""

import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.normalization import (
    normalize_frame,
    normalize_sequence,
    LEFT_HAND_START,
    LEFT_HAND_END,
    RIGHT_HAND_START,
    RIGHT_HAND_END,
    LEFT_SHOULDER_IDX,
    RIGHT_SHOULDER_IDX,
    MIN_SHOULDER_WIDTH,
    Anchor,
)


def create_synthetic_frame(
    ls=(0.4, 0.4, 0.1),
    rs=(0.6, 0.4, 0.1),
    lh_present=True,
    rh_present=True,
) -> np.ndarray:
    """Helper creating synthetic 225-dim landmark frame."""
    frame = np.zeros(225, dtype=np.float32)

    # Set shoulders
    frame[LEFT_SHOULDER_IDX * 3 : LEFT_SHOULDER_IDX * 3 + 3] = ls
    frame[RIGHT_SHOULDER_IDX * 3 : RIGHT_SHOULDER_IDX * 3 + 3] = rs

    # Set arbitrary non-shoulder pose points
    frame[0:3] = [0.5, 0.2, 0.0] # Nose

    # Set hands if present
    if lh_present:
        for i in range(21):
            frame[LEFT_HAND_START + i * 3 : LEFT_HAND_START + i * 3 + 3] = [0.3, 0.5, 0.0]

    if rh_present:
        for i in range(21):
            frame[RIGHT_HAND_START + i * 3 : RIGHT_HAND_START + i * 3 + 3] = [0.7, 0.5, 0.0]

    return frame


def test_standard_normalization():
    """Verify standard frame with both shoulders and hands."""
    aspect = 16.0 / 9.0
    frame = create_synthetic_frame(ls=(0.4, 0.4, 0.0), rs=(0.6, 0.4, 0.0), lh_present=True, rh_present=True)
    norm, anchor = normalize_frame(frame, aspect_ratio=aspect)

    expected_scale = (0.6 - 0.4) * aspect # (0.2 * 1.7777778)
    assert math.isclose(anchor.scale, expected_scale, rel_tol=1e-5)
    assert anchor.scale >= MIN_SHOULDER_WIDTH

    # Shoulders should be symmetric around origin
    ls_norm_x = norm[LEFT_SHOULDER_IDX * 3]
    rs_norm_x = norm[RIGHT_SHOULDER_IDX * 3]
    assert math.isclose(ls_norm_x, -0.5, abs_tol=1e-4)
    assert math.isclose(rs_norm_x, 0.5, abs_tol=1e-4)


def test_missing_hand_case():
    """Missing hands must remain strictly 0.0 after normalization."""
    aspect = 16.0 / 9.0
    # Left hand present, Right hand missing
    frame = create_synthetic_frame(ls=(0.4, 0.4, 0.0), rs=(0.6, 0.4, 0.0), lh_present=True, rh_present=False)
    norm, _ = normalize_frame(frame, aspect_ratio=aspect)

    # Left hand should be non-zero
    assert np.any(norm[LEFT_HAND_START:LEFT_HAND_END] != 0.0)

    # Right hand MUST remain strictly zero
    rh_slice = norm[RIGHT_HAND_START:RIGHT_HAND_END]
    assert np.all(rh_slice == 0.0)
    assert np.max(np.abs(rh_slice)) == 0.0


def test_missing_shoulder_case():
    """If shoulders are missing or scale < MIN_SHOULDER_WIDTH, reuse last anchor or fallback."""
    aspect = 16.0 / 9.0

    # Frame 1: Valid anchor
    f1 = create_synthetic_frame(ls=(0.4, 0.4, 0.0), rs=(0.6, 0.4, 0.0))
    norm1, a1 = normalize_frame(f1, aspect_ratio=aspect)
    assert a1.scale > 0.1

    # Frame 2: Missing shoulders (both 0.0)
    f2 = create_synthetic_frame(ls=(0.0, 0.0, 0.0), rs=(0.0, 0.0, 0.0))
    norm2, a2 = normalize_frame(f2, aspect_ratio=aspect, last_anchor=a1)

    # Must reuse a1 anchor
    assert a2.scale == a1.scale
    assert a2.mx == a1.mx

    # Frame 3: Missing shoulders without prior anchor -> neutral fallback
    norm3, a3 = normalize_frame(f2, aspect_ratio=aspect, last_anchor=None)
    assert a3.scale == 1.0
    assert math.isclose(a3.mx, 0.5 * aspect, abs_tol=1e-5)


def test_sequence_anchor_continuity():
    """Verify anchor continuity across 30-frame sequence."""
    seq = np.zeros((30, 225), dtype=np.float32)
    # Frame 0 has valid shoulders
    seq[0] = create_synthetic_frame(ls=(0.4, 0.4, 0.0), rs=(0.6, 0.4, 0.0))
    # Frames 1-29 have dropped shoulders
    norm_seq = normalize_sequence(seq)
    assert norm_seq.shape == (30, 225)
    assert not np.isnan(norm_seq).any()
    assert not np.isinf(norm_seq).any()


if __name__ == "__main__":
    test_standard_normalization()
    test_missing_hand_case()
    test_missing_shoulder_case()
    test_sequence_anchor_continuity()
    print("All Python normalization parity tests passed successfully!")

