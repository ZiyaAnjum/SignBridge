"""Vocabulary translations loader for SignBridge."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
VOCABULARY_FILE = ROOT_DIR / "docs" / "vocabulary.md"

# Cache
_TRANSLATIONS: Optional[Dict[str, Dict[str, str]]] = None


def get_translations() -> Dict[str, Dict[str, str]]:
    """Loads and caches multilingual translations from docs/vocabulary.md."""
    global _TRANSLATIONS
    if _TRANSLATIONS is not None:
        return _TRANSLATIONS

    table: Dict[str, Dict[str, str]] = {
        "idle": {"english": "idle", "hindi": "निष्क्रिय", "kannada": "ನಿಷ್ಕ್ರಿಯ"},
    }

    if VOCABULARY_FILE.exists():
        content = VOCABULARY_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 5:
                    label = cols[1].replace("`", "").strip().lower()
                    eng = cols[2].strip()
                    hin = cols[3].strip()
                    kan = cols[4].strip()
                    if label:
                        table[label] = {
                            "english": eng,
                            "hindi": hin,
                            "kannada": kan,
                        }

    _TRANSLATIONS = table
    return _TRANSLATIONS


def get_label_translations(label: Optional[str]) -> Dict[str, Optional[str]]:
    """Returns {english, hindi, kannada} for a given label, or None values if not found."""
    if not label:
        return {"english": None, "hindi": None, "kannada": None}

    translations = get_translations()
    if label in translations:
        return translations[label]

    return {
        "english": label.replace("_", " "),
        "hindi": None,
        "kannada": None,
    }

