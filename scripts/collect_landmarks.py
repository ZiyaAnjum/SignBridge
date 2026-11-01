"""
SignBridge ISL Landmark Data Collector
Captures 30-frame landmark sequences (~2 seconds) via webcam using MediaPipe Holistic.
Saves landmark arrays ONLY as NumPy .npy files (no raw video stored).

Directory Structure:
data/
  raw/
    signer_01/
      yes/
        sample_001.npy
        sample_002.npy
      no/
      ...
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.vocabulary import CLASSES, TRANSLATIONS, get_word_info


def extract_landmarks(results):
    """
    Extract Pose (33), Left Hand (21), and Right Hand (21) landmarks into a flat NumPy array.
    Shape: (33*3 + 21*3 + 21*3) = (75, 3) = 225 values per frame.
    Zero-pads if a hand is not detected.
    """
    import numpy as np

    # Pose: 33 landmarks (x, y, z)
    if results.pose_landmarks:
        pose = np.array([[lm.x, lm.y, lm.z] for lm in results.pose_landmarks.landmark], dtype=np.float32)
    else:
        pose = np.zeros((33, 3), dtype=np.float32)

    # Left Hand: 21 landmarks (x, y, z)
    if results.left_hand_landmarks:
        lh = np.array([[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark], dtype=np.float32)
    else:
        lh = np.zeros((21, 3), dtype=np.float32)

    # Right Hand: 21 landmarks (x, y, z)
    if results.right_hand_landmarks:
        rh = np.array([[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark], dtype=np.float32)
    else:
        rh = np.zeros((21, 3), dtype=np.float32)

    # Concatenate into (75, 3) and flatten to (225,)
    combined = np.concatenate([pose, lh, rh], axis=0)
    return combined.flatten()


def run_collection(signer_id: str, target_words: list, samples_per_word: int = 40, camera_idx: int = 0):
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        print("[ERROR] Required libraries not installed.")
        print("Please install: pip install opencv-python mediapipe numpy")
        return

    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(camera_idx)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {camera_idx}")
        return

    data_dir = ROOT_DIR / "data" / "raw" / signer_id
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f" SignBridge ISL Landmark Data Collection")
    print(f" Signer: {signer_id}")
    print(f" Words to record: {len(target_words)}")
    print(f" Samples target per word: {samples_per_word}")
    print(f" Controls: SPACE to start recording sample, 'q' to exit")
    print(f"=======================================================\n")

    SEQUENCE_LENGTH = 30  # 30 frames ~ 1.5 - 2.0 seconds

    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as holistic:
        for word in target_words:
            word_dir = data_dir / word
            word_dir.mkdir(parents=True, exist_ok=True)

            existing_samples = len(list(word_dir.glob("*.npy")))
            info = get_word_info(word)
            hi_text = info.get("hindi", "") if info else ""
            kn_text = info.get("kannada", "") if info else ""
            sign_desc = info.get("islrtc_sign", "") if info else ""

            sample_idx = existing_samples

            while sample_idx < samples_per_word:
                # Countdown / Ready stage
                print(f"\n>>> Next Word: '{word}' (Hi: {hi_text} | Kn: {kn_text})")
                print(f"    Sign Reference: {sign_desc}")
                print(f"    Sample {sample_idx + 1}/{samples_per_word}. Press SPACE to record, 'q' to quit.")

                waiting_for_trigger = True
                while waiting_for_trigger:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)
                    display = frame.copy()

                    cv2.putText(display, f"Word: {word.upper()} ({sample_idx + 1}/{samples_per_word})",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.putText(display, f"Signer: {signer_id}",
                                (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(display, "Press SPACE to start recording",
                                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    cv2.imshow("SignBridge Data Collection", display)
                    key = cv2.waitKey(10) & 0xFF
                    if key == ord(' '):
                        waiting_for_trigger = False
                    elif key == ord('q'):
                        print("Exiting data collection.")
                        cap.release()
                        cv2.destroyAllWindows()
                        return

                # 1-second countdown
                for count in [3, 2, 1]:
                    start_time = time.time()
                    while time.time() - start_time < 0.35:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        frame = cv2.flip(frame, 1)
                        cv2.putText(frame, f"GET READY: {count}", (200, 240),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 255), 3)
                        cv2.imshow("SignBridge Data Collection", frame)
                        cv2.waitKey(1)

                # Recording 30 frames
                sequence = []
                print(f"    [*] RECORDING: {word} (30 frames)...")

                for frame_num in range(SEQUENCE_LENGTH):
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.flip(frame, 1)
                    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image_rgb.flags.writeable = False
                    results = holistic.process(image_rgb)
                    image_rgb.flags.writeable = True

                    landmarks = extract_landmarks(results)
                    sequence.append(landmarks)

                    # Draw landmarks on display
                    mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                    mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

                    progress = int((frame_num + 1) / SEQUENCE_LENGTH * 200)
                    cv2.rectangle(frame, (20, 440), (20 + progress, 460), (0, 255, 0), -1)
                    cv2.putText(frame, f"RECORDING {frame_num + 1}/{SEQUENCE_LENGTH}",
                                (20, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                    cv2.imshow("SignBridge Data Collection", frame)
                    cv2.waitKey(1)

                # Save sample as .npy array
                if len(sequence) == SEQUENCE_LENGTH:
                    sequence_arr = np.array(sequence, dtype=np.float32)  # Shape: (30, 225)
                    save_path = word_dir / f"sample_{sample_idx + 1:04d}.npy"
                    np.save(str(save_path), sequence_arr)
                    print(f"    [+] Saved sample to {save_path.name}")
                    sample_idx += 1
                else:
                    print("    [-] Frame drop occurred. Retrying sample...")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[SUCCESS] Session completed.")


def main():
    parser = argparse.ArgumentParser(description="SignBridge ISL Landmark Data Collector")
    parser.add_argument("--signer", type=str, required=True, help="Signer identifier (e.g. signer_01)")
    parser.add_argument("--words", type=str, default="all", help="Comma-separated word labels or 'all'")
    parser.add_argument("--samples", type=int, default=40, help="Target samples per word (default: 40)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    args = parser.parse_args()

    if args.words == "all":
        target_words = CLASSES
    else:
        target_words = [w.strip() for w in args.words.split(",") if w.strip() in CLASSES]

    run_collection(
        signer_id=args.signer,
        target_words=target_words,
        samples_per_word=args.samples,
        camera_idx=args.camera,
    )


if __name__ == "__main__":
    main()

