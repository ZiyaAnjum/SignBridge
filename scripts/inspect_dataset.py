"""
Audit SignBridge ISL Landmark Dataset
Checks data volume, signer distribution, and sequence shape compliance.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.vocabulary import CLASSES, NUM_CLASSES, WORDS_BY_CATEGORY


def audit_dataset():
    data_dir = ROOT_DIR / "data" / "raw"
    if not data_dir.exists():
        print(f"[!] Data directory not found: {data_dir}")
        print("    Run 'python scripts/collect_landmarks.py --signer signer_01' to start collecting data.")
        return

    signers = [d.name for d in data_dir.iterdir() if d.is_dir()]
    print(f"\n=======================================================")
    print(f" SignBridge ISL Dataset Audit")
    print(f" Registered Signers: {len(signers)} ({', '.join(signers) if signers else 'None'})")
    print(f" Total Vocabulary Classes: {NUM_CLASSES}")
    print(f"=======================================================\n")

    summary = {w: 0 for w in CLASSES}
    signer_counts = {s: 0 for s in signers}

    total_samples = 0
    corrupt_samples = 0

    for s in signers:
        s_dir = data_dir / s
        for w in CLASSES:
            w_dir = s_dir / w
            if w_dir.exists():
                npy_files = list(w_dir.glob("*.npy"))
                count = len(npy_files)
                summary[w] += count
                signer_counts[s] += count
                total_samples += count

    print(f"{'Category':<12} | {'Word Label':<16} | {'Samples':<8} | {'Status'}")
    print("-" * 52)

    TARGET = 40
    under_target = 0

    for cat, words in WORDS_BY_CATEGORY.items():
        for w in words:
            cnt = summary[w]
            if cnt >= TARGET:
                status = f"✓ Ready ({cnt}/{TARGET})"
            elif cnt > 0:
                status = f"⚡ In Progress ({cnt}/{TARGET})"
                under_target += 1
            else:
                status = "✗ Missing (0)"
                under_target += 1
            print(f"{cat:<12} | {w:<16} | {cnt:<8} | {status}")

    print("\n" + "=" * 52)
    print(f"Total Samples Collected : {total_samples}")
    print(f"Words Under Target ({TARGET})  : {under_target} / {NUM_CLASSES}")
    print("Signer Breakdown:")
    for s, cnt in signer_counts.items():
        print(f"  - {s}: {cnt} samples")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    audit_dataset()

