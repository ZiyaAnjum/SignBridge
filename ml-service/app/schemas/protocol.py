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
    label: str = Field(..., description="Predicted class label in snake_case (e.g. 'doctor', 'emergency')")
    english: str = Field(..., description="English translated text")
    hindi: str = Field(..., description="Hindi translated text")
    kannada: str = Field(..., description="Kannada translated text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    is_emergency: bool = Field(default=False, description="Flag indicating emergency distress sign")
    top_guesses: List[TopGuess] = Field(default_factory=list, description="Top candidate predictions for low-confidence recovery")
    timestamp: float = Field(default_factory=time.time)

