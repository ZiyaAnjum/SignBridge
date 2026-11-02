"""SignBridge Landmark Data Collector (OpenCV + MediaPipe Holistic).
Records 30-frame skeletal coordinate sequences (225 features per frame) at 15 FPS.
Saves ONLY landmark arrays into data/landmarks/<signer>/<label>/sample_XXXX.npy (zero video stored).
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np

# Directory Resolution
SCRIPT_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = SCRIPT_DIR.parent
ROOT_DIR = ML_SERVICE_DIR.parent
DEFAULT_DATA_DIR = ML_SERVICE_DIR / "data" / "landmarks"
VOCABULARY_PATH = ROOT_DIR / "docs" / "vocabulary.md"

SIGNER_REGEX = re.compile(r"^[a-z0-9_]+$")
SAMPLE_RATE_FPS = 15.0
FRAME_INTERVAL_SEC = 1.0 / SAMPLE_RATE_FPS  # ~0.0667s (66.67ms)
SEQUENCE_LENGTH = 30  # 30 frames per sample


def load_allowed_labels(vocab_file: Path) -> Set[str]:
    """Extract valid vocabulary labels from docs/vocabulary.md plus 'idle'."""
    allowed: Set[str] = {"idle"}
    if not vocab_file.exists():
        return allowed

    content = vocab_file.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 2:
                label_raw = cols[1].replace("`", "").strip().lower()
                if label_raw and SIGNER_REGEX.match(label_raw):
                    allowed.add(label_raw)
    return allowed


def extract_landmarks(results) -> np.ndarray:
    """Extract 33 Pose + 21 Left Hand + 21 Right Hand landmarks into a 225-dim float32 array.
    Zero-fills any undetected hands/limbs.
    """
    # 1. Pose: 33 points (x, y, z)
    if results.pose_landmarks:
        pose = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        pose = np.zeros((33, 3), dtype=np.float32)

    # 2. Left Hand: 21 points (x, y, z)
    if results.left_hand_landmarks:
        lh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        lh = np.zeros((21, 3), dtype=np.float32)

    # 3. Right Hand: 21 points (x, y, z)
    if results.right_hand_landmarks:
        rh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        rh = np.zeros((21, 3), dtype=np.float32)

    return np.concatenate([pose, lh, rh], axis=0).flatten()


def run_collection(
    signer: str,
    target_words: List[str],
    samples_per_word: int = 40,
    output_dir: Path = DEFAULT_DATA_DIR,
    camera_idx: int = 0,
) -> None:
    """Capture 30-frame landmark sequences via webcam at 15 FPS."""
    if not SIGNER_REGEX.match(signer):
        raise ValueError(f"Invalid signer ID '{signer}'. Must match ^[a-z0-9_]+$")

    try:
        import cv2
        import mediapipe as mp
    except ImportError:
        print("[ERROR] Required packages not found. Run pip install opencv-python mediapipe numpy")
        sys.exit(1)

    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(camera_idx)
    if not cap.isOpened():
        print(f"[ERROR] Could not open webcam at index {camera_idx}.")
        sys.exit(1)

    # Ensure output stays inside landmarks directory
    resolved_root = output_dir.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print(" SignBridge Landmark Data Collector (Python 3.11)")
    print(f" Signer: {signer}")
    print(f" Target words ({len(target_words)}): {', '.join(target_words[:8])}...")
    print(f" Rate: 15 FPS by timestamp | Sequence: 30 frames (2.0s)")
    print(f" Output: {resolved_root / signer}")
    print(" Controls: [SPACE] Record | [s] Skip | [q] Quit")
    print("=======================================================\n")

    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:
        for word in target_words:
            word_dir = (resolved_root / signer / word).resolve()
            if not str(word_dir).startswith(str(resolved_root)):
                raise PermissionError("Path traversal attempt detected.")
            word_dir.mkdir(parents=True, exist_ok=True)

            existing = list(word_dir.glob("sample_*.npy"))
            sample_idx = len(existing)

            while sample_idx < samples_per_word:
                print(f"\n>>> Next Word: [{word.upper()}] | Sample {sample_idx + 1}/{samples_per_word}")

                # Wait for trigger
                waiting = True
                skip = False
                while waiting:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Display is mirrored for user convenience; coordinates extracted from UNMIRRORED frame
                    display = cv2.flip(frame, 1)
                    cv2.putText(
                        display,
                        f"Target: {word.upper()} ({sample_idx + 1}/{samples_per_word})",
                        (24, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (14, 107, 99),
                        2,
                    )
                    cv2.putText(
                        display,
                        f"Signer: {signer} | [SPACE] Record | [s] Skip | [q] Quit",
                        (24, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (27, 31, 30),
                        1,
                    )

                    cv2.imshow("SignBridge Data Collector", display)
                    key = cv2.waitKey(10) & 0xFF
                    if key == ord(" "):
                        waiting = False
                    elif key == ord("s"):
                        skip = True
                        break
                    elif key == ord("q"):
                        cap.release()
                        cv2.destroyAllWindows()
                        print("\nSession exited.")
                        return

                if skip:
                    break

                # 3-2-1 Countdown
                for count in [3, 2, 1]:
                    t0 = time.time()
                    while time.time() - t0 < 0.4:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        display = cv2.flip(frame, 1)
                        cv2.putText(
                            display,
                            f"START IN: {count}",
                            (200, 240),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.5,
                            (0, 90, 138),
                            3,
                        )
                        cv2.imshow("SignBridge Data Collector", display)
                        cv2.waitKey(1)

                # Record 30 frames at fixed 15 FPS
                sequence: List[np.ndarray] = []
                last_frame_time = 0.0

                while len(sequence) < SEQUENCE_LENGTH:
                    ret, raw_frame = cap.read()
                    if not ret:
                        break

                    now = time.time()
                    if now - last_frame_time < FRAME_INTERVAL_SEC:
                        continue
                    last_frame_time = now

                    # MediaPipe processes UNMIRRORED frame
                    rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    results = holistic.process(rgb)
                    rgb.flags.writeable = True

                    landmarks = extract_landmarks(results)
                    sequence.append(landmarks)

                    # Mirrored preview display with landmark wireframe
                    display = cv2.flip(raw_frame, 1)
                    progress = int(len(sequence) / SEQUENCE_LENGTH * 240)
                    cv2.rectangle(display, (24, 440), (24 + progress, 456), (46, 125, 50), -1)
                    cv2.putText(
                        display,
                        f"RECORDING {len(sequence)}/{SEQUENCE_LENGTH} (15 FPS)",
                        (24, 420),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (46, 125, 50),
                        2,
                    )
                    cv2.imshow("SignBridge Data Collector", display)
                    cv2.waitKey(1)

                if len(sequence) == SEQUENCE_LENGTH:
                    sequence_arr = np.array(sequence, dtype=np.float32)  # Shape (30, 225)
                    save_path = word_dir / f"sample_{sample_idx + 1:04d}.npy"
                    np.save(str(save_path), sequence_arr)
                    print(f"    [+] Saved: {save_path.relative_to(ML_SERVICE_DIR)} (Shape: {sequence_arr.shape})")
                    sample_idx += 1
                else:
                    print("    [-] Frame drop. Retrying sample...")

    cap.release()
    cv2.destroyAllWindows()
    print("\nCollection finished.")


def main() -> None:
    parser = argparse.ArgumentParser(description="SignBridge ISL Landmark Data Collector")
    parser.add_argument("--signer", type=str, default="signer_01", help="Signer ID (^[a-z0-9_]+$)")
    parser.add_argument("--words", type=str, default="all", help="Comma-separated labels or 'all'")
    parser.add_argument("--samples", type=int, default=40, help="Samples per word (default: 40)")
    parser.add_argument("--camera", type=int, default=0, help="Webcam device index (default: 0)")
    args = parser.parse_args()

    allowed = load_allowed_labels(VOCABULARY_PATH)
    if args.words == "all":
        words = sorted(list(allowed))
    else:
        words = [w.strip().lower() for w in args.words.split(",") if w.strip().lower() in allowed]

    if not words:
        print("[ERROR] No valid words selected. Check docs/vocabulary.md.")
        sys.exit(1)

    run_collection(
        signer=args.signer,
        target_words=words,
        samples_per_word=args.samples,
        camera_idx=args.camera,
    )


if __name__ == "__main__":
    main()
