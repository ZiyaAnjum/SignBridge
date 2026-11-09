"""Unit tests for check_data.py auditor.
Verifies all quality checks in a temporary directory outside data/landmarks.
"""

import tempfile
from pathlib import Path
import sys
import numpy as np

# Path setup
TESTS_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = TESTS_DIR.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from scripts.check_data import run_data_check, audit_file


def test_consecutive_hand_detection_rule():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Sample with hands present for only 4 consecutive frames (should be flagged)
        sample_short_run = np.zeros((30, 225), dtype=np.float32)
        # Left hand start=99, end=162
        for t in range(5, 9):  # 4 frames
            sample_short_run[t, 100] = 0.5

        # Sample with hands present for 10 consecutive frames (should PASS)
        sample_long_run = np.zeros((30, 225), dtype=np.float32)
        for t in range(5, 15):  # 10 frames
            sample_long_run[t, 100] = 0.5

        # Sample for 'idle' class with 0 hand frames (should PASS because idle doesn't need hands)
        sample_idle = np.zeros((30, 225), dtype=np.float32)
        # Add basic shoulder pose to avoid total anchor fallback
        sample_idle[:, 33] = 0.4
        sample_idle[:, 36] = 0.6

        p_short = tmp_path / "short.npy"
        p_long = tmp_path / "long.npy"
        p_idle = tmp_path / "idle.npy"

        np.save(p_short, sample_short_run)
        np.save(p_long, sample_long_run)
        np.save(p_idle, sample_idle)

        res_short, _ = audit_file(p_short, "signer_a", "help")
        res_long, _ = audit_file(p_long, "signer_a", "help")
        res_idle, _ = audit_file(p_idle, "signer_a", "idle")

        assert any("LOW_CONSECUTIVE_HANDS" in r for r in res_short.reasons), "Expected short run to be flagged"
        assert not any("LOW_CONSECUTIVE_HANDS" in r for r in res_long.reasons), "Expected long run to pass"
        assert not any("LOW_CONSECUTIVE_HANDS" in r for r in res_idle.reasons), "Expected idle class with no hands to pass"


def test_duplicate_detection_and_readiness():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Signers and classes
        signers = ["signer1", "signer2", "signer3"]
        classes = ["yes", "no", "help"]

        # Base sample with valid shoulders and hands
        base_sample = np.zeros((30, 225), dtype=np.float32)
        # Left/Right shoulder pose (indices 33..38)
        base_sample[:, 33] = 0.4  # left shoulder x
        base_sample[:, 34] = 0.5  # left shoulder y
        base_sample[:, 36] = 0.6  # right shoulder x
        base_sample[:, 37] = 0.5  # right shoulder y
        # 12 frames of hand detection
        base_sample[5:17, 100] = 0.5

        # Create dataset
        for signer in signers:
            for c in classes:
                for idx in range(20):
                    p = tmp_path / signer / c / f"sample_{idx:04d}.npy"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    # Add tiny variation so not all are duplicates
                    s = base_sample.copy()
                    s[0, 0] = float(idx) + (0.1 if signer == "signer1" else 0.2)
                    np.save(p, s)

        # Now add one exact duplicate pair
        dup1 = tmp_path / "signer1" / "yes" / "sample_0000.npy"
        dup2 = tmp_path / "signer2" / "yes" / "sample_9999.npy"
        dup2.parent.mkdir(parents=True, exist_ok=True)
        np.save(dup2, np.load(dup1))

        is_ready, summary = run_data_check(tmp_path, words=classes)

        assert summary["duplicates_count"] >= 1, "Should have detected the duplicate group"
        assert is_ready is True, "Dataset should be READY when all 3 signers have 20 samples for target classes"


if __name__ == "__main__":
    print("Running test_consecutive_hand_detection_rule...")
    test_consecutive_hand_detection_rule()
    print("Running test_duplicate_detection_and_readiness...")
    test_duplicate_detection_and_readiness()
    print("\n[OK] ALL CHECK_DATA TESTS PASSED SUCCESSFULLY!")

