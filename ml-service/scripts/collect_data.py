"""SignBridge Landmark Collector wrapper inside ml-service."""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.collect_data import main

if __name__ == "__main__":
    main()

