"""Data protocols and Pydantic schemas for SignBridge API and WebSocket streaming."""
from __future__ import annotations

import time
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="ok", description="Service health state")
    service: str = Field(default="signbridge-ml-service", description="Service identifier")
    version: str = Field(default="0.1.0", description="API version")
    device: str = Field(default="cpu", description="Compute device (cpu/cuda)")
    model_loaded: bool = Field(default=False, description="Whether ML weights are loaded in memory")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")


class TopGuess(BaseModel):
    """Candidate label prediction with confidence score."""
    label: str
    confidence: float


class LandmarkFrame(BaseModel):
    """Single landmark frame or sequence payload sent from frontend webcam."""
    landmarks: List[float] = Field(..., description="Flattened 225-dim landmark values (Pose + 2 Hands)")
    frame_index: Optional[int] = Field(default=0, description="Sequential index within current clip")
    timestamp: Optional[float] = Field(default_factory=time.time)


class PredictionResult(BaseModel):
    """Inference response delivered over WebSocket to frontend."""
    label: Optional[str] = Field(default=None, description="Predicted class label in snake_case or None if low confidence/idle")
    english: Optional[str] = Field(default=None, description="English translated text")
    hindi: Optional[str] = Field(default=None, description="Hindi translated text")
    kannada: Optional[str] = Field(default=None, description="Kannada translated text")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model prediction confidence score")
    is_emergency: bool = Field(default=False, description="Flag indicating emergency distress sign")
    top_guesses: List[TopGuess] = Field(default_factory=list, description="Top candidate predictions for low-confidence recovery")
    model_loaded: bool = Field(default=False, description="Whether ML weights are loaded in memory")
    state: Optional[str] = Field(default=None, description="Operational state: 'ready', 'no_signer', 'buffering', 'low_confidence'")
    inference_latency_ms: float = Field(default=0.0, description="Inference execution latency in milliseconds")
    reason: Optional[str] = Field(default=None, description="Reason if model is not loaded or frame skipped")
    timestamp: float = Field(default_factory=time.time)

