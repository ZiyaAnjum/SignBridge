"""
SignBridge ISL Landmark Data Collector
Captures 30-frame landmark sequences (~1.5-2.0s) via webcam using MediaPipe Holistic.
Extracts Pose (33), Left Hand (21), and Right Hand (21) keypoints (225 features per frame).
Saves landmark arrays ONLY as NumPy .npy files into data/landmarks/<label>/ (no raw video stored).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Root resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT_DIR / "data" / "landmarks"
VOCABULARY_PATH = ROOT_DIR / "docs" / "vocabulary.md"


def parse_vocabulary(vocab_file: Path) -> List[Dict[str, str]]:
    """Parse word definitions and translations from docs/vocabulary.md table."""
    words: List[Dict[str, str]] = []
    if not vocab_file.exists():
        print(f"[WARN] Vocabulary file not found at {vocab_file}. Using fallback core list.")
        return [
            {"label": "yes", "english": "yes", "category": "core"},
            {"label": "no", "english": "no", "category": "core"},
            {"label": "help", "english": "help", "category": "core"},
            {"label": "emergency", "english": "emergency", "category": "emergency"},
        ]

    content = vocab_file.read_text(encoding="utf-8")
    table_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("|") and not line.strip().startswith("| #") and not line.strip().startswith("|---")
    ]

    for line in table_lines:
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) >= 6:
            label_match = re.search(r"`([a-z_]+)`", cols[1])
            label = label_match.group(1) if label_match else cols[1].strip().lower()
            words.append({
                "label": label,
                "english": cols[2],
                "hindi": cols[3],
                "kannada": cols[4],
                "category": cols[5],
                "summary": cols[6] if len(cols) > 6 else "",
            })
    return words


def extract_landmarks(results) -> np.ndarray:
    """
    Extract Pose (33), Left Hand (21), and Right Hand (21) landmarks.
    Output: 1D NumPy array of shape (225,) [75 points x (x, y, z)].
    Zero-fills any missing limb/hand.
    """
    # Pose: 33 landmarks
    if results.pose_landmarks:
        pose = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        pose = np.zeros((33, 3), dtype=np.float32)

    # Left Hand: 21 landmarks
    if results.left_hand_landmarks:
        lh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        lh = np.zeros((21, 3), dtype=np.float32)

    # Right Hand: 21 landmarks
    if results.right_hand_landmarks:
        rh = np.array(
            [[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark],
            dtype=np.float32,
        )
    else:
        rh = np.zeros((21, 3), dtype=np.float32)

    return np.concatenate([pose, lh, rh], axis=0).flatten()


def run_collection(
    target_words: List[Dict[str, str]],
    samples_per_word: int = 40,
    output_dir: Path = DEFAULT_DATA_DIR,
    camera_idx: int = 0,
) -> None:
    """Main loop capturing landmark sequences."""
    try:
        import cv2
        import mediapipe as mp
    except ImportError:
        print("[ERROR] Required packages not found.")
        print("Please run: pip install opencv-python mediapipe numpy")
        return

    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(camera_idx)
    if not cap.isOpened():
        print(f"[ERROR] Could not open webcam at index {camera_idx}.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    SEQUENCE_LENGTH = 30  # 30 frames per gesture sequence

    print("\n=======================================================")
    print(" SignBridge ISL Landmark Data Collector")
    print(f" Target words: {len(target_words)}")
    print(f" Samples target per word: {samples_per_word}")
    print(f" Output folder: {output_dir}")
    print(" Controls:")
    print("   [SPACE] : Start 3-second countdown to record sample")
    print("   [s]     : Skip to next word")
    print("   [q]     : Quit collection session")
    print("=======================================================\n")

    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:
        for word_info in target_words:
            label = word_info["label"]
            word_dir = output_dir / label
            word_dir.mkdir(parents=True, exist_ok=True)

            existing_files = list(word_dir.glob("sample_*.npy"))
            sample_idx = len(existing_files)

            while sample_idx < samples_per_word:
                print(f"\n>>> Word: [{label.upper()}] ({word_info.get('english', label)})")
                if "hindi" in word_info and "kannada" in word_info:
                    print(f"    Translations: Hindi: {word_info['hindi']} | Kannada: {word_info['kannada']}")
                if "summary" in word_info:
                    print(f"    Sign guide: {word_info['summary']}")
                print(f"    Sample {sample_idx + 1}/{samples_per_word}. Press SPACE to record.")

                # Wait for user trigger
                waiting_for_trigger = True
                skip_word = False
                while waiting_for_trigger:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)
                    display = frame.copy()

                    cv2.putText(
                        display,
                        f"Target: {label.upper()} ({sample_idx + 1}/{samples_per_word})",
                        (24, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (14, 107, 99),  # Accent teal #0E6B63 in BGR
                        2,
                    )
                    cv2.putText(
                        display,
                        "Press SPACE to record | 's' skip | 'q' quit",
                        (24, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (27, 31, 30),
                        1,
                    )

                    cv2.imshow("SignBridge Collector", display)
                    key = cv2.waitKey(10) & 0xFF
                    if key == ord(" "):
                        waiting_for_trigger = False
                    elif key == ord("s"):
                        skip_word = True
                        break
                    elif key == ord("q"):
                        cap.release()
                        cv2.destroyAllWindows()
                        print("\nSession exited by user.")
                        return

                if skip_word:
                    break

                # 3-2-1 Countdown
                for count in [3, 2, 1]:
                    t_start = time.time()
                    while time.time() - t_start < 0.4:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.flip(frame, 1)
                        cv2.putText(
                            frame,
                            f"START IN: {count}",
                            (200, 240),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.5,
                            (0, 90, 138),  # Warm amber
                            3,
                        )
                        cv2.imshow("SignBridge Collector", frame)
                        cv2.waitKey(1)

                # Capture 30 landmark frames
                sequence: List[np.ndarray] = []
                for f_idx in range(SEQUENCE_LENGTH):
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    results = holistic.process(rgb)
                    rgb.flags.writeable = True

                    landmarks = extract_landmarks(results)
                    sequence.append(landmarks)

                    # Draw visual feedback
                    mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

                    # Recording progress bar
                    progress_width = int((f_idx + 1) / SEQUENCE_LENGTH * 240)
                    cv2.rectangle(frame, (24, 440), (24 + progress_width, 456), (46, 125, 50), -1)
                    cv2.putText(
                        frame,
                        f"RECORDING {f_idx + 1}/{SEQUENCE_LENGTH}",
                        (24, 420),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (46, 125, 50),
                        2,
                    )

                    cv2.imshow("SignBridge Collector", frame)
                    cv2.waitKey(1)

                # Save ONLY landmarks array (.npy)
                if len(sequence) == SEQUENCE_LENGTH:
                    sequence_arr = np.array(sequence, dtype=np.float32)  # Shape (30, 225)
                    save_path = word_dir / f"sample_{sample_idx + 1:04d}.npy"
                    np.save(str(save_path), sequence_arr)
                    print(f"    [+] Saved landmarks: {save_path.relative_to(ROOT_DIR)} (Shape: {sequence_arr.shape})")
                    sample_idx += 1
                else:
                    print("    [-] Frame drop occurred. Retrying sample...")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[COMPLETE] Landmark collection session finished.")


def main() -> None:
    parser = argparse.ArgumentParser(description="SignBridge ISL Landmark Data Collector")
    parser.add_argument(
        "--vocab-file",
        type=Path,
        default=VOCABULARY_PATH,
        help="Path to docs/vocabulary.md",
    )
    parser.add_argument(
        "--words",
        type=str,
        default="all",
        help="Comma-separated word labels or 'all'",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=40,
        help="Samples target per word (default: 40)",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Output directory (default: data/landmarks)",
    )
    args = parser.parse_args()

    vocab = parse_vocabulary(args.vocab_file)
    if args.words != "all":
        selected = {w.strip().lower() for w in args.words.split(",")}
        vocab = [w for w in vocab if w["label"] in selected]

    if not vocab:
        print("[ERROR] No valid words selected for collection.")
        sys.exit(1)

    run_collection(
        target_words=vocab,
        samples_per_word=args.samples,
        output_dir=args.output_dir,
        camera_idx=args.camera,
    )


if __name__ == "__main__":
    main()

