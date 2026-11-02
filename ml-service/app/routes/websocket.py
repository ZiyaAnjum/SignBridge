"""WebSocket endpoint for live landmark sequence streaming and prediction delivery."""
from __future__ import annotations

import json
import logging
import random
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.config import settings
from app.schemas.protocol import PredictionResult, TopGuess

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("signbridge.ws")

# Mock vocabulary samples for skeleton testing
SAMPLE_PREDICTIONS = [
    {"label": "doctor", "english": "doctor", "hindi": "डॉक्टर", "kannada": "ವೈದ್ಯರು", "is_emergency": False},
    {"label": "help", "english": "help", "hindi": "मदद", "kannada": "ಸಹಾಯ", "is_emergency": False},
    {"label": "water", "english": "water", "hindi": "पानी", "kannada": "ನೀರು", "is_emergency": False},
    {"label": "fever", "english": "fever", "hindi": "बुखार", "kannada": "ಜ್ವರ", "is_emergency": False},
    {"label": "pain", "english": "pain", "hindi": "दर्द", "kannada": "ನೋವು", "is_emergency": True},
    {"label": "emergency", "english": "emergency", "hindi": "आपातकाल", "kannada": "ತುರ್ತು", "is_emergency": True},
    {"label": "account", "english": "account", "hindi": "खाता", "kannada": "ಖಾತೆ", "is_emergency": False},
    {"label": "deposit", "english": "deposit", "hindi": "जमा", "kannada": "ಠೇವಣಿ", "is_emergency": False},
]


@router.websocket("/ws/landmarks")
async def websocket_landmarks(websocket: WebSocket) -> None:
    """
    Accept stream of skeletal landmark frames from webcam.
    Privacy guarantee: receives landmark coordinate arrays only; no video or image frames are received or stored.
    Returns: PredictionResult with confidence and translations.
    """
    await websocket.accept()
    logger.info("Client connected to /ws/landmarks")

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)

            # Check if payload contains landmarks or heartbeat ping
            if "ping" in data:
                await websocket.send_text(json.dumps({"pong": True, "timestamp": time.time()}))
                continue

            # Echo dummy prediction with variable confidence for skeleton testing
            selected = random.choice(SAMPLE_PREDICTIONS)
            confidence = round(random.uniform(0.68, 0.98), 2)
            
            top_guesses = [
                TopGuess(label=selected["label"], confidence=confidence),
                TopGuess(label="appointment" if selected["label"] != "appointment" else "test", confidence=round(1.0 - confidence, 2)),
            ]

            result = PredictionResult(
                label=selected["label"],
                english=selected["english"],
                hindi=selected["hindi"],
                kannada=selected["kannada"],
                confidence=confidence,
                is_emergency=selected["is_emergency"],
                top_guesses=top_guesses,
                timestamp=time.time(),
            )

            await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/landmarks")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}", exc_info=True)
        await websocket.close()

