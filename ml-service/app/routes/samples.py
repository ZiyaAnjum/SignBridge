"""Samples collection endpoints for SignBridge."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import numpy as np

router = APIRouter(prefix="/samples", tags=["Samples"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent.parent
LANDMARKS_BASE_DIR = (ML_SERVICE_DIR / "data" / "landmarks").resolve()
VOCABULARY_FILE = (ROOT_DIR / "docs" / "vocabulary.md").resolve()

SIGNER_PATTERN = re.compile(r"^[a-z0-9_]+$")


def get_allowed_labels() -> Set[str]:
    """Parse allowed vocabulary labels from docs/vocabulary.md plus 'idle'."""
    allowed: Set[str] = {"idle"}
    if not VOCABULARY_FILE.exists():
        return allowed

    content = VOCABULARY_FILE.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 2:
                label_clean = cols[1].replace("`", "").strip().lower()
                if label_clean and SIGNER_PATTERN.match(label_clean):
                    allowed.add(label_clean)
    return allowed


class SampleUploadPayload(BaseModel):
    """Payload for uploading a 30-frame recorded landmark sequence."""
    signer: str = Field(..., description="Signer identifier matching ^[a-z0-9_]+$")
    label: str = Field(..., description="Target vocabulary label or 'idle'")
    landmarks: List[List[float]] = Field(
        ...,
        description="30 frames x 225-dimensional unmirrored landmark coordinate arrays",
    )


class SampleUploadResponse(BaseModel):
    status: str = "saved"
    signer: str
    label: str
    filename: str
    word_total: int


@router.get("/counts")
async def get_sample_counts() -> Dict[str, object]:
    """Return live per-signer and per-word sample counts from data/landmarks/."""
    counts_by_word: Dict[str, int] = {}
    counts_by_signer: Dict[str, int] = {}
    total = 0

    if LANDMARKS_BASE_DIR.exists():
        for npy_file in LANDMARKS_BASE_DIR.glob("*/*/*.npy"):
            total += 1
            signer = npy_file.parent.parent.name
            word = npy_file.parent.name

            counts_by_signer[signer] = counts_by_signer.get(signer, 0) + 1
            counts_by_word[word] = counts_by_word.get(word, 0) + 1

    return {
        "total_samples": total,
        "by_word": counts_by_word,
        "by_signer": counts_by_signer,
    }


@router.post("", response_model=SampleUploadResponse, status_code=status.HTTP_201_CREATED)
async def save_sample(payload: SampleUploadPayload) -> SampleUploadResponse:
    """Validate and persist a 30-frame landmark sample array."""
    # 1. Signer format validation
    signer = payload.signer.strip().lower()
    if not SIGNER_PATTERN.match(signer):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signer ID '{payload.signer}'. Must match ^[a-z0-9_]+$",
        )

    # 2. Label validation against docs/vocabulary.md + 'idle'
    label = payload.label.strip().lower()
    allowed_labels = get_allowed_labels()
    if label not in allowed_labels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Label '{payload.label}' is not in approved vocabulary list.",
        )

    # 3. Shape validation: exactly 30 frames x 225 coordinates
    if len(payload.landmarks) != 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected exactly 30 frames, got {len(payload.landmarks)}.",
        )

    for idx, frame in enumerate(payload.landmarks):
        if len(frame) != 225:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Frame {idx} has invalid length {len(frame)} (expected 225).",
            )

    # 4. Resolve path securely and guarantee it stays inside data/landmarks/
    target_dir = (LANDMARKS_BASE_DIR / signer / label).resolve()
    try:
        target_dir.relative_to(LANDMARKS_BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security violation: Path traversal detected outside data/landmarks/.",
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    existing_samples = list(target_dir.glob("sample_*.npy"))
    sample_index = len(existing_samples) + 1
    sample_filename = f"sample_{sample_index:04d}.npy"
    target_file = target_dir / sample_filename

    # Save landmark coordinates array (Shape: (30, 225))
    seq_arr = np.array(payload.landmarks, dtype=np.float32)
    np.save(str(target_file), seq_arr)

    return SampleUploadResponse(
        status="saved",
        signer=signer,
        label=label,
        filename=sample_filename,
        word_total=sample_index,
    )

