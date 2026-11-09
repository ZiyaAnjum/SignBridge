"""SignBridge Dataset Quality & Integrity Auditor.

Scans data/landmarks/<signer>/<label>/sample_XXXX.npy and verifies:
- Dataset completeness and readiness for training.
- Per-signer and per-class sample counts.
- Hand detection rates per-signer and per-class distributions (min / median / max).
- Consecutive hand detection run (flagging non-idle samples where max consecutive hand run < 8 frames).
- Duplicate detection across files.
- Samples with shoulder anchor fallbacks or corrupted / all-zero data.
- Ends with a READY / NOT READY summary for training:
  * At least 3 signers
  * At least 20 samples per class
  * Every class present for every signer
  Lists exactly what is missing.

NOTE: This script performs read-only audits. No files are modified or deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# Path setup to import from app
SCRIPT_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = SCRIPT_DIR.parent
ROOT_DIR = ML_SERVICE_DIR.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.core.normalization import (
    LEFT_HAND_START,
    LEFT_HAND_END,
    RIGHT_HAND_START,
    RIGHT_HAND_END,
    compute_shoulder_anchor,
    DEFAULT_ASPECT_RATIO,
)

DEFAULT_LANDMARKS_DIR = ML_SERVICE_DIR / "data" / "landmarks"
VOCABULARY_FILE = ROOT_DIR / "docs" / "vocabulary.md"
MIN_CONSECUTIVE_HAND_FRAMES = 8  # Flag non-idle sample if longest run of hands < 8 frames
MIN_SAMPLES_PER_CLASS = 20
MIN_SIGNERS = 3


def load_vocabulary_labels(vocab_file: Path = VOCABULARY_FILE) -> List[str]:
    """Parse ordered vocabulary labels from docs/vocabulary.md + 'idle'."""
    labels: List[str] = []
    if vocab_file.exists():
        content = vocab_file.read_text(encoding="utf-8")
        label_pattern = re.compile(r"^[a-z0-9_]+$")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 2:
                    word = cols[1].replace("`", "").strip().lower()
                    if word and label_pattern.match(word) and word not in labels:
                        labels.append(word)

    if "idle" not in labels:
        labels.append("idle")
    return labels


class FileAuditResult:
    def __init__(self, path: Path, signer: str, label: str):
        self.path = path
        self.signer = signer
        self.label = label
        self.is_valid_shape = True
        self.is_all_zero = False
        self.has_nan_inf = False
        self.frames_count = 0
        self.left_hand_frames = 0
        self.right_hand_frames = 0
        self.any_hand_frames = 0
        self.max_consecutive_hand_frames = 0
        self.anchor_fallback_frames = 0
        self.file_hash: Optional[str] = None
        self.reasons: List[str] = []

    @property
    def is_suspect(self) -> bool:
        return len(self.reasons) > 0


def audit_file(file_path: Path, signer: str, label: str) -> Tuple[FileAuditResult, Optional[bytes]]:
    result = FileAuditResult(file_path, signer, label)

    try:
        data = np.load(file_path)
    except Exception as exc:
        result.is_valid_shape = False
        result.reasons.append(f"CORRUPT_FILE: Unable to load numpy array ({exc})")
        return result, None

    if data.ndim != 2 or data.shape != (30, 225):
        result.is_valid_shape = False
        result.reasons.append(f"INVALID_SHAPE: Expected (30, 225), got {data.shape}")
        return result, None

    result.frames_count = data.shape[0]

    # Compute array hash for duplicate detection
    array_bytes = data.tobytes()
    result.file_hash = hashlib.sha256(array_bytes).hexdigest()

    # Check NaN / Inf
    if np.isnan(data).any() or np.isinf(data).any():
        result.has_nan_inf = True
        result.reasons.append("NAN_OR_INF: Contains NaN or Inf coordinates")

    # Check All-Zero
    if np.all(data == 0.0):
        result.is_all_zero = True
        result.reasons.append("ALL_ZERO: All coordinates are 0.0")
        return result, array_bytes

    # Frame-by-frame analysis
    last_anchor = None
    consecutive_run = 0
    max_run = 0

    for t in range(result.frames_count):
        frame = data[t]

        # Check hands
        lh_detected = bool(np.any(frame[LEFT_HAND_START:LEFT_HAND_END] != 0.0))
        rh_detected = bool(np.any(frame[RIGHT_HAND_START:RIGHT_HAND_END] != 0.0))
        has_hand = lh_detected or rh_detected

        if lh_detected:
            result.left_hand_frames += 1
        if rh_detected:
            result.right_hand_frames += 1
        if has_hand:
            result.any_hand_frames += 1
            consecutive_run += 1
            if consecutive_run > max_run:
                max_run = consecutive_run
        else:
            consecutive_run = 0

        # Check shoulder anchor fallback
        anchor, is_valid = compute_shoulder_anchor(frame, DEFAULT_ASPECT_RATIO, last_anchor)
        if not is_valid:
            result.anchor_fallback_frames += 1
        else:
            last_anchor = anchor

    result.max_consecutive_hand_frames = max_run

    # Consecutive hand run rule for hand-requiring classes
    if label != "idle":
        if max_run < MIN_CONSECUTIVE_HAND_FRAMES:
            result.reasons.append(
                f"LOW_CONSECUTIVE_HANDS: Max consecutive hand run is {max_run} frames "
                f"(< {MIN_CONSECUTIVE_HAND_FRAMES} required for class '{label}')"
            )

    # Flag heavy anchor fallback
    if result.anchor_fallback_frames > 0:
        fb_pct = round((result.anchor_fallback_frames / result.frames_count) * 100, 1)
        if result.anchor_fallback_frames == result.frames_count:
            result.reasons.append("TOTAL_ANCHOR_FALLBACK: Shoulder midpoint missing in all 30 frames")
        elif fb_pct >= 50.0:
            result.reasons.append(
                f"HEAVY_ANCHOR_FALLBACK: Shoulder midpoint missing in {result.anchor_fallback_frames}/{result.frames_count} frames ({fb_pct}%)"
            )

    return result, array_bytes


def run_data_check(
    data_dir: Path,
    words: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, any]]:
    """Runs a complete dataset audit and prints detailed findings.
    
    Returns:
        (is_ready, audit_summary_dict)
    """
    resolved_dir = data_dir.resolve()
    print("=" * 76)
    print(" SignBridge Dataset Quality & Readiness Audit (Read-Only)")
    print(f" Directory: {resolved_dir}")
    print("=" * 76)

    # Determine target vocabulary
    vocab_labels = load_vocabulary_labels()
    if words:
        target_labels = [w.strip().lower() for w in words if w.strip()]
    else:
        target_labels = vocab_labels

    if not resolved_dir.exists():
        print(f"\n[INFO] Directory not found: {resolved_dir}")
        print("No samples recorded yet.")
        _print_readiness_summary([], {}, {}, target_labels)
        return False, {"ready": False, "samples": 0}

    all_files = sorted(list(resolved_dir.glob("*/*/*.npy")))
    if not all_files:
        print("\n[INFO] No .npy sample files found in directory.")
        print("Directory structure expected: data/landmarks/<signer>/<label>/sample_XXXX.npy")
        _print_readiness_summary([], {}, {}, target_labels)
        return False, {"ready": False, "samples": 0}

    total_files = len(all_files)
    signer_samples: Dict[str, int] = defaultdict(int)
    class_samples: Dict[str, int] = defaultdict(int)
    signer_class_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # Per-signer stats
    signer_frames: Dict[str, int] = defaultdict(int)
    signer_lh_frames: Dict[str, int] = defaultdict(int)
    signer_rh_frames: Dict[str, int] = defaultdict(int)
    signer_any_frames: Dict[str, int] = defaultdict(int)

    # Per-class hand frames distribution: class -> list of any_hand_frames count
    class_hand_frames: Dict[str, List[int]] = defaultdict(list)

    total_frames = 0
    total_lh_frames = 0
    total_rh_frames = 0
    total_any_hand_frames = 0
    samples_with_fallback = 0
    total_fallback_frames = 0
    all_zero_samples = 0

    # Duplicate detection: hash -> list of file paths
    hash_to_files: Dict[str, List[Path]] = defaultdict(list)
    suspect_files: List[FileAuditResult] = []

    for file_path in all_files:
        signer = file_path.parent.parent.name
        label = file_path.parent.name
        signer_samples[signer] += 1
        class_samples[label] += 1
        signer_class_matrix[signer][label] += 1

        res, _ = audit_file(file_path, signer, label)

        if res.file_hash:
            hash_to_files[res.file_hash].append(file_path)

        if res.is_all_zero:
            all_zero_samples += 1

        if res.anchor_fallback_frames > 0:
            samples_with_fallback += 1
            total_fallback_frames += res.anchor_fallback_frames

        total_frames += res.frames_count
        total_lh_frames += res.left_hand_frames
        total_rh_frames += res.right_hand_frames
        total_any_hand_frames += res.any_hand_frames

        signer_frames[signer] += res.frames_count
        signer_lh_frames[signer] += res.left_hand_frames
        signer_rh_frames[signer] += res.right_hand_frames
        signer_any_frames[signer] += res.any_hand_frames

        class_hand_frames[label].append(res.any_hand_frames)

        if res.is_suspect:
            suspect_files.append(res)

    # Detect duplicates
    duplicates: List[List[Path]] = [paths for paths in hash_to_files.values() if len(paths) > 1]
    for dup_group in duplicates:
        for p in dup_group:
            # Add duplicate note to suspect files if not already logged
            for s in suspect_files:
                if s.path == p and not any("DUPLICATE_SAMPLE" in r for r in s.reasons):
                    other = [str(x.relative_to(resolved_dir)) for x in dup_group if x != p]
                    s.reasons.append(f"DUPLICATE_SAMPLE: Identical array to {', '.join(other)}")

    # 1. Summary Header
    print(f"\n[1] DATASET OVERVIEW")
    print(f"  Total Samples Analyzed : {total_files}")
    print(f"  Distinct Signers       : {len(signer_samples)}")
    print(f"  Distinct Classes Present: {len(class_samples)}")
    print(f"  Target Classes Checked : {len(target_labels)}")
    print(f"  Total Frames Evaluated : {total_frames}")

    # 2. Per-Signer Counts
    print(f"\n[2] SAMPLES PER SIGNER")
    for signer, count in sorted(signer_samples.items()):
        print(f"  - {signer:<22} : {count:>4} samples")

    # 3. Per-Class Counts
    print(f"\n[3] SAMPLES PER CLASS")
    sorted_classes = sorted(class_samples.items(), key=lambda x: (-x[1], x[0]))
    for label, count in sorted_classes:
        tag = " (idle class)" if label == "idle" else ""
        print(f"  - {label:<22} : {count:>4} samples{tag}")

    # 4. Per-Signer Hand Detection Rates
    print(f"\n[4] PER-SIGNER HAND DETECTION RATES")
    print(f"  {'Signer':<18} | {'Left Hand %':<12} | {'Right Hand %':<12} | {'Either Hand %':<14} | {'Samples':<7}")
    print(f"  {'-'*18}-+-{'-'*12}-+-{'-'*12}-+-{'-'*14}-+-{'-'*7}")
    for signer in sorted(signer_samples.keys()):
        sf = signer_frames[signer]
        if sf > 0:
            slh = (signer_lh_frames[signer] / sf) * 100
            srh = (signer_rh_frames[signer] / sf) * 100
            sany = (signer_any_frames[signer] / sf) * 100
            print(f"  {signer:<18} | {slh:>10.1f}% | {srh:>10.1f}% | {sany:>12.1f}% | {signer_samples[signer]:>7}")

    # 5. Class Hand Visibility Distribution (min / median / max)
    print(f"\n[5] HAND VISIBILITY DISTRIBUTION PER CLASS (Frames with hand out of 30: min / median / max)")
    print(f"  {'Class':<22} | {'Min':<6} | {'Median':<8} | {'Max':<6} | {'Samples':<7}")
    print(f"  {'-'*22}-+-{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*7}")
    for label in sorted(class_hand_frames.keys()):
        frames_list = class_hand_frames[label]
        f_min = min(frames_list)
        f_median = float(np.median(frames_list))
        f_max = max(frames_list)
        print(f"  {label:<22} | {f_min:>4}   | {f_median:>6.1f}   | {f_max:>4}   | {len(frames_list):>7}")

    # 6. Anchor Stability
    fb_sample_pct = (samples_with_fallback / total_files) * 100 if total_files else 0.0
    fb_frame_pct = (total_fallback_frames / total_frames) * 100 if total_frames else 0.0
    print(f"\n[6] ANCHOR STABILITY & FALLBACK")
    print(f"  - Samples with any fallback : {samples_with_fallback}/{total_files} ({fb_sample_pct:.1f}%)")
    print(f"  - Total fallback frames     : {total_fallback_frames}/{total_frames} ({fb_frame_pct:.1f}%)")
    print(f"  - All-zero samples          : {all_zero_samples}")

    # 7. Duplicate Samples Check
    print(f"\n[7] DUPLICATE SAMPLES AUDIT")
    if not duplicates:
        print("  [OK] No duplicate landmark files detected.")
    else:
        print(f"  [FLAG] Found {len(duplicates)} duplicate group(s) with identical arrays:")
        for idx, group in enumerate(duplicates, 1):
            print(f"    Group {idx}:")
            for p in group:
                print(f"      - {p.relative_to(resolved_dir)}")

    # 8. Suspect Files Audit
    print(f"\n[8] SUSPECT FILES AUDIT ({len(suspect_files)} flagged)")
    if not suspect_files:
        print("  [OK] All samples passed quality thresholds! Zero suspect files.")
    else:
        for item in suspect_files:
            rel_path = item.path.relative_to(resolved_dir)
            print(f"  [FLAG] {rel_path}:")
            for r in item.reasons:
                print(f"         - {r}")

    # 9. Readiness Summary
    is_ready = _print_readiness_summary(
        signers=list(signer_samples.keys()),
        class_samples=class_samples,
        signer_class_matrix=signer_class_matrix,
        target_labels=target_labels,
    )

    print("\n" + "=" * 76)
    print(" [NOTE] Read-only audit complete. No files were modified or deleted.")
    print("=" * 76 + "\n")

    summary = {
        "ready": is_ready,
        "total_files": total_files,
        "signers": list(signer_samples.keys()),
        "classes_present": list(class_samples.keys()),
        "suspect_count": len(suspect_files),
        "duplicates_count": len(duplicates),
    }
    return is_ready, summary


def _print_readiness_summary(
    signers: List[str],
    class_samples: Dict[str, int],
    signer_class_matrix: Dict[str, Dict[str, int]],
    target_labels: List[str],
) -> bool:
    """Evaluates readiness criteria:
    1. At least 3 signers.
    2. At least 20 samples per class.
    3. Every class present for every signer.
    """
    print(f"\n[9] TRAINING READINESS EVALUATION")

    missing_items: List[str] = []

    # Criterion 1: At least 3 signers
    num_signers = len(signers)
    if num_signers < MIN_SIGNERS:
        missing_items.append(
            f"Signer Count: Found {num_signers} signer(s) ({', '.join(sorted(signers)) if signers else 'none'}), but at least {MIN_SIGNERS} signers are required."
        )

    # Criterion 2: At least 20 samples per class
    classes_below_target = []
    for label in target_labels:
        count = class_samples.get(label, 0)
        if count < MIN_SAMPLES_PER_CLASS:
            classes_below_target.append((label, count))

    if classes_below_target:
        missing_items.append(
            f"Samples per class: {len(classes_below_target)}/{len(target_labels)} classes have fewer than {MIN_SAMPLES_PER_CLASS} samples."
        )

    # Criterion 3: Every class present for every signer
    signer_missing_classes: Dict[str, List[str]] = {}
    for signer in signers:
        missing_for_s = [lbl for lbl in target_labels if signer_class_matrix[signer].get(lbl, 0) == 0]
        if missing_for_s:
            signer_missing_classes[signer] = missing_for_s

    if signer_missing_classes:
        missing_items.append(
            f"Signer-Class Coverage: Not all target classes are recorded for each signer."
        )

    if not missing_items:
        print("  STATUS: [READY FOR TRAINING]")
        print("  All criteria met:")
        print(f"  * {num_signers} signers (>= {MIN_SIGNERS} required)")
        print(f"  * All {len(target_labels)} classes have >= {MIN_SAMPLES_PER_CLASS} samples")
        print(f"  * Complete coverage: every class is present for every signer")
        return True
    else:
        print("  STATUS: [NOT READY FOR TRAINING]")
        print("  Missing prerequisites:")
        for item in missing_items:
            print(f"  * {item}")

        if classes_below_target:
            print("\n  Class sample breakdown (current / required):")
            # Show top missing classes
            for lbl, count in classes_below_target[:15]:
                print(f"    - {lbl:<20} : {count:>2} / {MIN_SAMPLES_PER_CLASS}")
            if len(classes_below_target) > 15:
                print(f"    ... and {len(classes_below_target) - 15} more classes below {MIN_SAMPLES_PER_CLASS} samples.")

        if signer_missing_classes:
            print("\n  Missing classes per signer:")
            for s, missing_lbls in signer_missing_classes.items():
                print(f"    - {s}: missing {len(missing_lbls)} classes ({', '.join(missing_lbls[:5])}{'...' if len(missing_lbls) > 5 else ''})")

        return False


def main():
    parser = argparse.ArgumentParser(description="SignBridge Dataset Quality & Readiness Auditor")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_LANDMARKS_DIR,
        help="Path to landmarks dataset folder (default: data/landmarks)",
    )
    parser.add_argument(
        "--words",
        type=str,
        default=None,
        help="Comma-separated subset of words to audit (e.g. 'yes,no,help,idle'). Defaults to all vocabulary.",
    )
    args = parser.parse_args()

    words_list = [w.strip() for w in args.words.split(",")] if args.words else None
    is_ready, _ = run_data_check(args.data_dir, words=words_list)
    # Exit code: 0 if ready, 1 if not ready
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    main()
