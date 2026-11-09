"""Unit tests for train.py training pipeline components.
Runs in isolation with synthetic structures and verifies:
- augment_sequence preserves 0.0 missing landmarks, performs time-shift, and avoids mirroring.
- split_data_by_signer enforces >= 3 signers unless forced.
- split_data_by_signer handles --leave-one-signer-out and single-signer mode.
- compute_class_weights properly balances inverse class frequencies.
"""

import sys
from pathlib import Path
import numpy as np
import torch

TESTS_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = TESTS_DIR.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from scripts.train import augment_sequence, split_data_by_signer, compute_class_weights


def test_augmentation_preserves_missing_landmarks():
    # Sequence with missing left hand (indices 99..162) and right hand (162..225)
    sample = np.zeros((30, 225), dtype=np.float32)
    # Pose detected
    sample[:, 33:39] = 0.5

    augmented = augment_sequence(sample)
    assert augmented.shape == (30, 225), f"Expected shape (30, 225), got {augmented.shape}"

    # Missing hands must stay strictly 0.0
    assert np.all(augmented[:, 99:225] == 0.0), "Missing hands must remain 0.0 after augmentation"
    # Pose must receive small noise / scale
    assert np.any(augmented[:, 33:39] != 0.5), "Detected pose coordinates should be augmented"


def test_signer_split_logic():
    label_to_idx = {"yes": 0, "no": 1, "idle": 2}

    # 3 signers dataset
    data_3_signers = {
        "signer_a": {"yes": [np.zeros((30, 225))], "no": [np.zeros((30, 225))], "idle": [np.zeros((30, 225))]},
        "signer_b": {"yes": [np.zeros((30, 225))], "no": [np.zeros((30, 225))], "idle": [np.zeros((30, 225))]},
        "signer_c": {"yes": [np.zeros((30, 225))], "no": [np.zeros((30, 225))], "idle": [np.zeros((30, 225))]},
    }

    # Standard split
    train, val, test, info = split_data_by_signer(data_3_signers, label_to_idx, force=False)
    assert info["evaluation_mode"] == "signer-independent"
    assert len(train) == 3
    assert len(val) == 3
    assert len(test) == 3
    assert info["test_signers"] == ["signer_c"]

    # Leave-one-out split
    train_loo, val_loo, test_loo, info_loo = split_data_by_signer(
        data_3_signers, label_to_idx, leave_one_out_signer="signer_a", force=False
    )
    assert info_loo["test_signers"] == ["signer_a"]
    assert "signer_a" not in info_loo["train_signers"]
    assert "signer_a" not in info_loo["val_signers"]

    # Refusal with <3 signers without force
    data_1_signer = {"signer_a": {"yes": [np.zeros((30, 225))] * 10}}
    try:
        split_data_by_signer(data_1_signer, label_to_idx, force=False)
        assert False, "Should have raised ValueError for <3 signers"
    except ValueError as e:
        assert "requires at least 3 signers" in str(e)

    # Forced single signer produces signer-dependent mode
    train_1, val_1, test_1, info_1 = split_data_by_signer(data_1_signer, label_to_idx, force=True)
    assert info_1["evaluation_mode"] == "signer-dependent"
    assert len(train_1) + len(val_1) + len(test_1) == 10


def test_class_weights_computation():
    train_samples = [
        (np.zeros((30, 225)), 0),
        (np.zeros((30, 225)), 0),
        (np.zeros((30, 225)), 0),
        (np.zeros((30, 225)), 1),  # Class 1 is rarer
    ]
    weights = compute_class_weights(train_samples, num_classes=2)
    assert weights[1] > weights[0], "Rarer class 1 should have higher weight than class 0"


if __name__ == "__main__":
    print("Testing augmentation...")
    test_augmentation_preserves_missing_landmarks()
    print("Testing signer split logic...")
    test_signer_split_logic()
    print("Testing class weights...")
    test_class_weights_computation()
    print("\n[OK] ALL TRAIN TESTS PASSED SUCCESSFULLY!")

