"""
Vocabulary definitions, mappings, and translation utilities for SignBridge ISL.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_CONFIG_PATH = Path(__file__).resolve().parent / "vocabulary.json"

with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
    _VOCAB_DATA: Dict[str, Any] = json.load(f)

# Classes in canonical order (0 to 41)
CLASSES: List[str] = [item["label"] for item in _VOCAB_DATA["words"]]
NUM_CLASSES: int = len(CLASSES)

# Mapping dictionaries
LABEL_TO_ID: Dict[str, int] = {item["label"]: item["id"] for item in _VOCAB_DATA["words"]}
ID_TO_LABEL: Dict[int, str] = {item["id"]: item["label"] for item in _VOCAB_DATA["words"]}

# Domain / Category dictionary
CATEGORIES: List[str] = _VOCAB_DATA["categories"]

WORDS_BY_CATEGORY: Dict[str, List[str]] = {cat: [] for cat in CATEGORIES}
for item in _VOCAB_DATA["words"]:
    WORDS_BY_CATEGORY[item["category"]].append(item["label"])

# Translations lookup: label -> {english, hindi, kannada}
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    item["label"]: {
        "english": item["english"],
        "hindi": item["hindi"],
        "kannada": item["kannada"],
    }
    for item in _VOCAB_DATA["words"]
}


def get_word_info(label_or_id: str | int) -> Optional[Dict[str, Any]]:
    """Retrieve full metadata for a given word label or class index."""
    if isinstance(label_or_id, int):
        if 0 <= label_or_id < NUM_CLASSES:
            return _VOCAB_DATA["words"][label_or_id]
        return None
    for word in _VOCAB_DATA["words"]:
        if word["label"] == label_or_id:
            return word
    return None


def translate(label: str, target_lang: str = "english") -> str:
    """
    Translate an ISL class label to the target language.
    Supported target_lang: 'english', 'hindi', 'kannada'.
    """
    lang = target_lang.lower().strip()
    entry = TRANSLATIONS.get(label)
    if not entry:
        return label
    return entry.get(lang, entry["english"])

