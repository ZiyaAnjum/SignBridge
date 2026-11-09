"""SignBridge Model Training Pipeline.

Trains the SignBridgeGRU sequence classifier on recorded landmark arrays:
- Input: 30 frames x 225 coordinates (Pose + Left Hand + Right Hand).
- Dataset validation: Enforces readiness standards (>= 3 signers, >= 20 samples/class, complete coverage) unless --force is provided.
- Split: Strictly BY SIGNER to ensure cross-signer generalization. Supports --leave-one-signer-out.
  If forced with a single signer, reports explicitly as SIGNER-DEPENDENT.
- Training Augmentation: Gaussian noise (sigma=0.01), random scaling (0.9-1.1), small temporal shift.
  Zero coordinates (missing landmarks) remain zero. NO MIRRORING.
- Class weights: Inversely proportional to class frequencies for balanced loss.
- Early stopping: Monitored on validation loss (patience 10), restoring best model weights.
- Includes 'idle' class in training.
- Outputs:
  * models/signbridge_gru.pt
  * models/label_map.json
  * models/confusion_matrix.png
  * Detailed metrics (Accuracy, per-class Precision/Recall/F1, top confused pairs report).
- Supports --words to train on a subset.
- Supports --dry-run to verify pipeline end-to-end on synthetic data in a temporary directory.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Ensure headless matplotlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# Path setup to import from app
SCRIPT_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = SCRIPT_DIR.parent
ROOT_DIR = ML_SERVICE_DIR.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.ml.architecture import SignBridgeGRU
from scripts.check_data import load_vocabulary_labels, audit_file, run_data_check

DEFAULT_LANDMARKS_DIR = ML_SERVICE_DIR / "data" / "landmarks"
DEFAULT_OUTPUT_DIR = ML_SERVICE_DIR / "models"


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def augment_sequence(seq: np.ndarray) -> np.ndarray:
    """Applies ISL-safe augmentation only to detected landmarks:
    1. Small temporal shift of [-2, +2] frames.
    2. Random isotropic scaling in [0.9, 1.1] on nonzero landmarks.
    3. Small Gaussian noise (sigma=0.01) on nonzero landmarks.
    NO MIRRORING.
    """
    seq = seq.copy()
    num_frames, _ = seq.shape

    # 1. Temporal shift
    shift = int(np.random.randint(-2, 3))
    if shift > 0:
        pad = np.repeat(seq[:1], shift, axis=0)
        seq = np.vstack([pad, seq[:-shift]])
    elif shift < 0:
        pad = np.repeat(seq[-1:], -shift, axis=0)
        seq = np.vstack([seq[-shift:], pad])

    # Mask for detected coordinates (nonzero)
    mask = (seq != 0.0)

    # 2. Random isotropic scale
    scale = float(np.random.uniform(0.9, 1.1))
    seq[mask] = seq[mask] * scale

    # 3. Small Gaussian noise
    noise = np.random.normal(0.0, 0.01, size=seq.shape).astype(np.float32)
    seq[mask] = seq[mask] + noise[mask]

    return seq


class SignBridgeDataset(Dataset):
    """PyTorch Dataset for (30, 225) landmark samples."""

    def __init__(self, samples: List[Tuple[np.ndarray, int]], augment: bool = False):
        self.samples = samples
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        data, label_idx = self.samples[idx]
        if self.augment:
            data = augment_sequence(data)
        x_tensor = torch.from_numpy(data.astype(np.float32))
        y_tensor = torch.tensor(label_idx, dtype=torch.long)
        return x_tensor, y_tensor


def load_dataset(
    data_dir: Path,
    target_classes: List[str],
) -> Tuple[Dict[str, Dict[str, List[np.ndarray]]], Dict[str, int]]:
    """Loads all valid samples grouped by signer and label."""
    data_by_signer: Dict[str, Dict[str, List[np.ndarray]]] = defaultdict(lambda: defaultdict(list))
    class_counts: Dict[str, int] = defaultdict(int)

    all_files = sorted(list(data_dir.glob("*/*/*.npy")))
    for p in all_files:
        signer = p.parent.parent.name
        label = p.parent.name
        if label not in target_classes:
            continue

        try:
            arr = np.load(p)
            if arr.shape == (30, 225) and not np.isnan(arr).any() and not np.isinf(arr).any():
                data_by_signer[signer][label].append(arr)
                class_counts[label] += 1
        except Exception:
            continue

    return data_by_signer, class_counts


def create_synthetic_dry_run_dataset(tmp_dir: Path, target_classes: List[str]) -> Path:
    """Generates synthetic data in a temporary directory for dry-run verification."""
    signers = ["dry_signer1", "dry_signer2", "dry_signer3"]
    samples_per_class = 20

    for s_idx, signer in enumerate(signers):
        for c_idx, label in enumerate(target_classes):
            for i in range(samples_per_class):
                # Shape (30, 225)
                arr = np.zeros((30, 225), dtype=np.float32)

                # Base pose: shoulders
                # Left shoulder (indices 33..35), Right shoulder (indices 36..38)
                arr[:, 33] = 0.45 + (s_idx * 0.01)
                arr[:, 34] = 0.50
                arr[:, 36] = 0.55 + (s_idx * 0.01)
                arr[:, 37] = 0.50

                if label != "idle":
                    # Distinct class motion pattern for hands
                    # Left hand: 99..162, Right hand: 162..225
                    t = np.linspace(0, np.pi, 30)
                    freq = (c_idx + 1) * 0.5
                    movement = 0.1 * np.sin(t * freq)

                    for frame_idx in range(5, 25):  # 20 frames of active signing
                        # Right hand wrist
                        arr[frame_idx, 162] = 0.55 + movement[frame_idx] + (s_idx * 0.01)
                        arr[frame_idx, 163] = 0.50 - movement[frame_idx]
                        arr[frame_idx, 164] = 0.10
                        # Finger tips
                        arr[frame_idx, 174:186] = 0.05 * (c_idx + 1)

                p = tmp_dir / signer / label / f"sample_{i:04d}.npy"
                p.parent.mkdir(parents=True, exist_ok=True)
                np.save(p, arr)

    return tmp_dir


def split_data_by_signer(
    data_by_signer: Dict[str, Dict[str, List[np.ndarray]]],
    label_to_idx: Dict[str, int],
    leave_one_out_signer: Optional[str] = None,
    force: bool = False,
    seed: int = 42,
) -> Tuple[List[Tuple[np.ndarray, int]], List[Tuple[np.ndarray, int]], List[Tuple[np.ndarray, int]], Dict[str, any]]:
    """Splits samples strictly BY SIGNER to test cross-signer generalization."""
    signers = sorted(list(data_by_signer.keys()))
    num_signers = len(signers)

    split_info = {
        "train_signers": [],
        "val_signers": [],
        "test_signers": [],
        "evaluation_mode": "signer-independent",
    }

    if num_signers == 0:
        raise ValueError("Cannot train: zero signers found in dataset.")

    if num_signers < 3 and not force:
        raise ValueError(
            f"Dataset has only {num_signers} signer(s): {signers}. SignBridge requires at least 3 signers "
            "for cross-signer evaluation (train / val / test). Use --leave-one-signer-out or pass --force to override."
        )

    # CASE 1: Single signer (forced)
    if num_signers == 1:
        signer = signers[0]
        split_info["train_signers"] = [signer]
        split_info["val_signers"] = [signer]
        split_info["test_signers"] = [signer]
        split_info["evaluation_mode"] = "signer-dependent"

        print("\n" + "!" * 76)
        print(f" [WARNING] Only 1 signer present ('{signer}').")
        print(" Model will be trained and evaluated using stratified intra-signer split (70% train / 15% val / 15% test).")
        print(" RESULTS ARE STRICTLY SIGNER-DEPENDENT AND DO NOT REFLECT GENERALIZATION TO NEW USERS.")
        print("!" * 76 + "\n")

        train_samples, val_samples, test_samples = [], [], []
        rng = random.Random(seed)

        for label, samples in data_by_signer[signer].items():
            l_idx = label_to_idx[label]
            shuffled = list(samples)
            rng.shuffle(shuffled)
            n = len(shuffled)
            n_train = max(1, int(0.70 * n))
            n_val = max(1, int(0.15 * n)) if n >= 3 else 1

            for s in shuffled[:n_train]:
                train_samples.append((s, l_idx))
            for s in shuffled[n_train : n_train + n_val]:
                val_samples.append((s, l_idx))
            for s in shuffled[n_train + n_val :]:
                test_samples.append((s, l_idx))

        return train_samples, val_samples, test_samples, split_info

    # CASE 2: Leave-one-out specified
    if leave_one_out_signer:
        if leave_one_out_signer not in signers:
            raise ValueError(f"Requested leave-one-out signer '{leave_one_out_signer}' not found. Available signers: {signers}")

        test_signer = leave_one_out_signer
        remaining = [s for s in signers if s != test_signer]
        val_signer = remaining[-1]
        train_signers = remaining[:-1] if len(remaining) > 1 else [remaining[0]]

        split_info["train_signers"] = train_signers
        split_info["val_signers"] = [val_signer]
        split_info["test_signers"] = [test_signer]

    # CASE 3: Standard multi-signer split
    elif num_signers >= 3:
        # Assign 1 signer to test, 1 to val, remainder to train
        test_signer = signers[-1]
        val_signer = signers[-2]
        train_signers = signers[:-2]

        split_info["train_signers"] = train_signers
        split_info["val_signers"] = [val_signer]
        split_info["test_signers"] = [test_signer]

    # CASE 4: Exactly 2 signers (forced)
    else:
        split_info["train_signers"] = [signers[0]]
        split_info["val_signers"] = [signers[1]]
        split_info["test_signers"] = [signers[1]]
        split_info["evaluation_mode"] = "signer-separated (2 signers)"

    print(f"\n[SIGNER SPLIT CONFIGURATION]")
    print(f"  Mode            : {split_info['evaluation_mode']}")
    print(f"  Train Signers   : {', '.join(split_info['train_signers'])}")
    print(f"  Val Signers     : {', '.join(split_info['val_signers'])}")
    print(f"  Test Signers    : {', '.join(split_info['test_signers'])}")

    train_samples, val_samples, test_samples = [], [], []

    if num_signers == 2:
        # Signer 0 -> train, Signer 1 -> split between val and test
        rng = random.Random(seed)
        for label, samples in data_by_signer[signers[0]].items():
            l_idx = label_to_idx[label]
            for s in samples:
                train_samples.append((s, l_idx))

        for label, samples in data_by_signer[signers[1]].items():
            l_idx = label_to_idx[label]
            shuffled = list(samples)
            rng.shuffle(shuffled)
            mid = len(shuffled) // 2
            for s in shuffled[:mid]:
                val_samples.append((s, l_idx))
            for s in shuffled[mid:]:
                test_samples.append((s, l_idx))
    else:
        for s in split_info["train_signers"]:
            for label, samples in data_by_signer[s].items():
                l_idx = label_to_idx[label]
                for arr in samples:
                    train_samples.append((arr, l_idx))

        for s in split_info["val_signers"]:
            for label, samples in data_by_signer[s].items():
                l_idx = label_to_idx[label]
                for arr in samples:
                    val_samples.append((arr, l_idx))

        for s in split_info["test_signers"]:
            for label, samples in data_by_signer[s].items():
                l_idx = label_to_idx[label]
                for arr in samples:
                    test_samples.append((arr, l_idx))

    return train_samples, val_samples, test_samples, split_info


def compute_class_weights(train_samples: List[Tuple[np.ndarray, int]], num_classes: int) -> torch.Tensor:
    """Computes inverse-frequency class weights for cross-entropy loss."""
    counts = np.zeros(num_classes, dtype=np.float32)
    for _, y in train_samples:
        counts[y] += 1.0

    # Smooth zero-counts to avoid inf/nan
    total = len(train_samples)
    weights = np.zeros(num_classes, dtype=np.float32)
    for c in range(num_classes):
        cnt = max(1.0, counts[c])
        weights[c] = total / (num_classes * cnt)

    return torch.from_numpy(weights).float()


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    class_weights: torch.Tensor,
    device: torch.device,
    epochs: int = 50,
    lr: float = 0.001,
    patience: int = 10,
) -> Tuple[nn.Module, Dict[str, List[float]]]:
    """Runs model training with Adam, class-weighted CE, early stopping on validation loss."""
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    best_val_loss = float("inf")
    best_weights = None
    patience_counter = 0

    print("\n[TRAINING PROGRESS]")
    print(f"  {'Epoch':<7} | {'Train Loss':<11} | {'Train Acc':<10} | {'Val Loss':<10} | {'Val Acc':<10}")
    print(f"  {'-'*7}-+-{'-'*11}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    for epoch in range(1, epochs + 1):
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * batch_x.size(0)
            preds = torch.argmax(logits, dim=1)
            train_correct += (preds == batch_y).sum().item()
            train_total += batch_x.size(0)

        epoch_train_loss = train_loss / max(1, train_total)
        epoch_train_acc = train_correct / max(1, train_total)

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                logits = model(batch_x)
                loss = criterion(logits, batch_y)

                val_loss += loss.item() * batch_x.size(0)
                preds = torch.argmax(logits, dim=1)
                val_correct += (preds == batch_y).sum().item()
                val_total += batch_x.size(0)

        epoch_val_loss = val_loss / max(1, val_total)
        epoch_val_acc = val_correct / max(1, val_total)

        history["train_loss"].append(epoch_train_loss)
        history["train_acc"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_acc"].append(epoch_val_acc)

        print(
            f"  {epoch:>4}/{epochs:<2} | {epoch_train_loss:>10.4f} | {epoch_train_acc*100:>8.1f}% | "
            f"{epoch_val_loss:>9.4f} | {epoch_val_acc*100:>8.1f}%"
        )

        # Early stopping check
        if epoch_val_loss < best_val_loss - 1e-4:
            best_val_loss = epoch_val_loss
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience and epoch >= 10:
                print(f"\n  [EARLY STOPPING] Validation loss stopped improving for {patience} consecutive epochs.")
                break

    if best_weights is not None:
        model.load_state_dict(best_weights)
        print("  [RESTORE] Successfully restored best model weights from epoch with lowest val loss.")

    return model, history


def evaluate_model(
    model: nn.Module,
    test_loader: DataLoader,
    target_classes: List[str],
    device: torch.device,
    output_dir: Path,
) -> Tuple[float, str, List[Tuple[str, str, int, float]]]:
    """Evaluates on test set, writes confusion matrix plot, and computes top confused pairs."""
    model.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x = batch_x.to(device)
            logits = model(batch_x)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(batch_y.numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    acc = float(accuracy_score(all_targets, all_preds))
    report = classification_report(
        all_targets,
        all_preds,
        target_names=target_classes,
        labels=list(range(len(target_classes))),
        zero_division=0,
    )

    # Confusion matrix
    cm = confusion_matrix(all_targets, all_preds, labels=list(range(len(target_classes))))

    # Save confusion matrix plot
    output_dir.mkdir(parents=True, exist_ok=True)
    cm_path = output_dir / "confusion_matrix.png"
    _plot_confusion_matrix(cm, target_classes, cm_path)

    # Find top confused pairs (off-diagonal)
    confused_pairs = []
    for true_idx in range(len(target_classes)):
        class_total = cm[true_idx].sum()
        for pred_idx in range(len(target_classes)):
            if true_idx != pred_idx and cm[true_idx, pred_idx] > 0:
                cnt = int(cm[true_idx, pred_idx])
                pct = (cnt / class_total * 100.0) if class_total > 0 else 0.0
                confused_pairs.append((target_classes[true_idx], target_classes[pred_idx], cnt, pct))

    confused_pairs.sort(key=lambda x: -x[2])
    return acc, report, confused_pairs


def _plot_confusion_matrix(cm: np.ndarray, classes: List[str], save_path: Path) -> None:
    """Renders and saves a confusion matrix figure adhering to SignBridge design tokens."""
    num_classes = len(classes)
    fig_size = max(8, num_classes * 0.35)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))

    # Clean teal colormap matching --accent #0E6B63
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Greens)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=classes,
        yticklabels=classes,
        title="SignBridge ISL Confusion Matrix",
        ylabel="True Label",
        xlabel="Predicted Label",
    )

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)

    # Annotate numbers in cells if small number of classes
    if num_classes <= 20:
        thresh = cm.max() / 2.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                if val > 0:
                    ax.text(
                        j,
                        i,
                        format(val, "d"),
                        ha="center",
                        va="center",
                        color="white" if val > thresh else "black",
                        fontsize=7,
                    )

    fig.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def run_pipeline(
    data_dir: Path,
    output_dir: Path,
    words: Optional[List[str]] = None,
    epochs: int = 50,
    batch_size: int = 16,
    lr: float = 0.001,
    patience: int = 10,
    leave_one_out: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
    seed: int = 42,
) -> int:
    """Executes the complete end-to-end training and evaluation pipeline."""
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 76)
    print(" SignBridge ISL Neural Sequence Classifier Training")
    print(f" Timestamp : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Device    : {device}")
    print(f" Dry Run   : {dry_run}")
    print("=" * 76)

    # Setup target classes
    vocab_labels = load_vocabulary_labels()
    if words:
        target_classes = [w.strip().lower() for w in words if w.strip()]
        if "idle" not in target_classes:
            target_classes.append("idle")
    elif dry_run:
        # Default dry run subset for quick verification
        target_classes = ["yes", "no", "help", "emergency", "doctor", "water", "thank_you", "idle"]
    else:
        target_classes = vocab_labels

    label_to_idx = {lbl: idx for idx, lbl in enumerate(target_classes)}
    idx_to_label = {idx: lbl for idx, lbl in enumerate(target_classes)}
    num_classes = len(target_classes)

    temp_dry_run_dir = None
    try:
        if dry_run:
            print("\n[DRY RUN MODE ENABLED]")
            print("Creating synthetic dataset in temporary directory for pipeline verification...")
            temp_dry_run_dir = tempfile.TemporaryDirectory()
            effective_data_dir = create_synthetic_dry_run_dataset(Path(temp_dry_run_dir.name), target_classes)
            epochs = min(epochs, 2)  # Cap dry-run at 2 epochs
        else:
            effective_data_dir = data_dir
            # Enforce readiness check on real data
            is_ready, _ = run_data_check(effective_data_dir, words=target_classes)
            if not is_ready and not force:
                print("\n[ERROR] Dataset is NOT READY for training according to SignBridge quality standards.")
                print("Run 'python scripts/check_data.py' to review missing signers, sample counts, or coverage.")
                print("Pass --force to override this safety check.")
                return 1

        # Load samples
        data_by_signer, class_counts = load_dataset(effective_data_dir, target_classes)
        total_samples = sum(class_counts.values())

        if total_samples == 0:
            print(f"\n[ERROR] No valid samples found in {effective_data_dir}.")
            print("To verify the training pipeline end-to-end with synthetic data, run with --dry-run.")
            return 1

        print(f"\n[DATASET SUMMARY]")
        print(f"  Target Classes : {num_classes}")
        print(f"  Total Samples  : {total_samples}")
        print(f"  Signers Found  : {len(data_by_signer)} ({', '.join(sorted(data_by_signer.keys()))})")

        # Split data
        train_samples, val_samples, test_samples, split_info = split_data_by_signer(
            data_by_signer=data_by_signer,
            label_to_idx=label_to_idx,
            leave_one_out_signer=leave_one_out,
            force=force or dry_run,
            seed=seed,
        )

        print(f"\n[DATASET SPLIT COUNTS]")
        print(f"  Train Samples : {len(train_samples):>5}")
        print(f"  Val Samples   : {len(val_samples):>5}")
        print(f"  Test Samples  : {len(test_samples):>5}")

        # PyTorch DataLoaders
        train_dataset = SignBridgeDataset(train_samples, augment=True)
        val_dataset = SignBridgeDataset(val_samples, augment=False)
        test_dataset = SignBridgeDataset(test_samples, augment=False)

        effective_batch_size = max(1, min(batch_size, len(train_dataset)))
        train_loader = DataLoader(train_dataset, batch_size=effective_batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=effective_batch_size, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=effective_batch_size, shuffle=False)

        # Class weights
        class_weights = compute_class_weights(train_samples, num_classes)

        # Initialize Model
        model = SignBridgeGRU(
            num_classes=num_classes,
            input_size=225,
            hidden_size=64,
            num_layers=1,
            bidirectional=True,
            dropout=0.2,
        ).to(device)

        # Train model
        model, history = train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            class_weights=class_weights,
            device=device,
            epochs=epochs,
            lr=lr,
            patience=patience,
        )

        # Evaluate on test set
        test_acc, test_report, confused_pairs = evaluate_model(
            model=model,
            test_loader=test_loader,
            target_classes=target_classes,
            device=device,
            output_dir=output_dir,
        )

        # Save artifacts
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / "signbridge_gru.pt"
        torch.save(model.state_dict(), model_path)

        label_map_path = output_dir / "label_map.json"
        metadata = {
            "model_type": "SignBridgeGRU",
            "created_at": datetime.datetime.now().isoformat(),
            "input_size": 225,
            "sequence_length": 30,
            "hidden_size": 64,
            "num_layers": 1,
            "bidirectional": True,
            "dropout": 0.2,
            "num_classes": num_classes,
            "classes": target_classes,
            "label_to_id": label_to_idx,
            "id_to_label": {str(k): v for k, v in idx_to_label.items()},
            "train_signers": split_info["train_signers"],
            "val_signers": split_info["val_signers"],
            "test_signers": split_info["test_signers"],
            "evaluation_mode": split_info["evaluation_mode"],
            "test_accuracy": round(test_acc, 4),
        }
        with open(label_map_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Print Evaluation Summary
        print("\n" + "=" * 76)
        print(" FINAL EVALUATION RESULTS")
        print("=" * 76)
        print(f" Evaluation Mode : {split_info['evaluation_mode']}")
        print(f" Test Accuracy   : {test_acc * 100:.2f}%")
        print("\n[PER-CLASS CLASSIFICATION REPORT]")
        print(test_report)

        print("\n[TOP CONFUSED CLASS PAIRS]")
        if not confused_pairs:
            print("  [OK] No misclassifications observed on the test set!")
        else:
            for true_cls, pred_cls, count, pct in confused_pairs[:10]:
                print(f"  * '{true_cls}' misclassified as '{pred_cls}': {count} time(s) ({pct:.1f}% of true '{true_cls}')")

        print("\n[SAVED ARTIFACTS]")
        print(f"  * Model weights   : {model_path}")
        print(f"  * Label metadata  : {label_map_path}")
        print(f"  * Confusion matrix: {output_dir / 'confusion_matrix.png'}")
        print("=" * 76 + "\n")

        return 0

    finally:
        if temp_dry_run_dir is not None:
            temp_dry_run_dir.cleanup()


def main():
    parser = argparse.ArgumentParser(description="SignBridge ISL Model Training Pipeline")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_LANDMARKS_DIR,
        help="Path to landmarks dataset folder (default: data/landmarks)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save model weights and label map (default: models)",
    )
    parser.add_argument(
        "--words",
        type=str,
        default=None,
        help="Comma-separated subset of classes to train on (e.g. 'yes,no,help,idle'). Defaults to all vocabulary.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs (default: 50, dry-run capped at 2)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size (default: 16)",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Learning rate for Adam optimizer (default: 0.001)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=10,
        help="Early stopping patience in epochs (default: 10)",
    )
    parser.add_argument(
        "--leave-one-signer-out",
        type=str,
        default=None,
        help="Specific signer to hold out for test evaluation (e.g. 'signer3')",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override readiness checks and train even with insufficient signers or samples.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Train for 2 epochs on synthetic data in a temp directory to verify pipeline end-to-end.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()
    words_list = [w.strip() for w in args.words.split(",")] if args.words else None

    exit_code = run_pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        words=words_list,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        leave_one_out=args.leave_one_signer_out,
        force=args.force,
        dry_run=args.dry_run,
        seed=args.seed,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
