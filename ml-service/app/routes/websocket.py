"""WebSocket endpoint for live landmark streaming and real-time inference."""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.ml.engine import get_engine
from app.ml.session import ConnectionSession, MAX_MESSAGE_BYTES

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger("signbridge.ws")

# Small thread executor to keep the asyncio event loop completely unblocked during ML forward passes
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml_infer")


@router.websocket("/ws/landmarks")
async def websocket_landmarks(websocket: WebSocket) -> None:
    """Live landmark sequence streaming endpoint.
    
    Guarantees:
    - Privacy: processes coordinate arrays only; no images or video are received or stored.
    - CORS: verified against allowed local frontend origins.
    - Buffer isolation: one rolling 30-frame buffer per connection, cleared on disconnect.
    - Input validation: exactly 225 finite floats per frame; message size and rate limits enforced.
    - Off-thread inference: forward pass executed in thread pool every 3 frames.
    - Temporal smoothing, repetition suppression, and high-confidence emergency alerts.
    """
    # 1. CORS Origin Verification
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.CORS_ORIGINS:
        logger.warning(f"Rejected WebSocket connection from unauthorized origin: {origin}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info("Client connected to /ws/landmarks")

    # Dedicated connection session (isolated per connection, zero shared global state)
    session = ConnectionSession()

    try:
        while True:
            raw_text = await websocket.receive_text()

            # 2. Limit message byte size
            if len(raw_text) > MAX_MESSAGE_BYTES:
                await websocket.send_text(
                    json.dumps({
                        "error": "message_too_large",
                        "detail": f"Payload size {len(raw_text)} exceeds maximum {MAX_MESSAGE_BYTES} bytes",
                    })
                )
                continue

            try:
                data = json.loads(raw_text)
            except Exception as exc:
                await websocket.send_text(
                    json.dumps({"error": "invalid_json", "detail": str(exc)})
                )
                continue

            # 3. Heartbeat & Control Commands
            if isinstance(data, dict):
                if "ping" in data:
                    await websocket.send_text(json.dumps({"pong": True, "timestamp": time.time()}))
                    continue
                if data.get("action") == "reset" or data.get("reset"):
                    session.clear()
                    await websocket.send_text(json.dumps({"status": "cleared"}))
                    continue

            # 4. Rate Limiting Check
            if session.check_rate_limit():
                await websocket.send_text(
                    json.dumps({
                        "error": "rate_limit_exceeded",
                        "detail": "Rate limit exceeded (maximum 45 frames per second)",
                    })
                )
                continue

            # 5. Extract and Validate Landmarks
            raw_landmarks = None
            if isinstance(data, dict):
                raw_landmarks = data.get("landmarks")
            elif isinstance(data, list):
                raw_landmarks = data

            is_valid, err_msg, frame_arr = session.validate_frame(raw_landmarks)
            if not is_valid:
                await websocket.send_text(
                    json.dumps({"error": "malformed_frame", "detail": err_msg})
                )
                continue

            # Push valid frame into the per-connection rolling 30-frame buffer
            session.push_frame(frame_arr)

            # 6. Check Model Availability
            engine = get_engine()
            if not engine.model_loaded:
                # Use dummy fallback response when model is not available or metadata mismatched
                fallback = session.create_fallback_result(
                    reason=engine.reason or "Model weights or label map not loaded"
                )
                await websocket.send_text(fallback.model_dump_json())
                continue

            # 7. Run Inference Every 3 Frames when Buffer is Full
            if session.should_run_inference():
                # Enforce single in-flight inference per connection
                if session.is_inferring:
                    continue

                # Check signer presence in the rolling 30-frame window
                has_signer, signer_reason = session.check_signer_presence()
                if not has_signer:
                    no_signer_res = session.create_no_signer_result(
                        reason=signer_reason or "Step into the frame",
                        model_loaded=engine.model_loaded,
                    )
                    await websocket.send_text(no_signer_res.model_dump_json())
                    continue

                session.is_inferring = True
                try:
                    t_start = time.perf_counter()
                    norm_seq = session.get_normalized_sequence()

                    # Execute model inference in thread pool to prevent blocking asyncio loop
                    loop = asyncio.get_running_loop()
                    top_label, top_conf, all_sorted = await loop.run_in_executor(
                        _executor,
                        engine.predict,
                        norm_seq,
                    )
                    latency_ms = (time.perf_counter() - t_start) * 1000.0

                    # Process smoothing, repetition suppression, and emergency rules
                    prediction_result = session.process_prediction(
                        current_label=top_label,
                        current_conf=top_conf,
                        all_sorted=all_sorted,
                        latency_ms=latency_ms,
                    )
                    await websocket.send_text(prediction_result.model_dump_json())
                finally:
                    session.is_inferring = False

            elif len(session.buffer) < 30:
                # Buffer accumulating initial frames
                buffering_result = session.create_fallback_result(
                    reason=f"Buffering frames ({len(session.buffer)}/30)"
                )
                # Indicate model is ready even while buffer fills
                buffering_result.model_loaded = True
                await websocket.send_text(buffering_result.model_dump_json())

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/landmarks")
    except Exception as exc:
        logger.error(f"Unexpected WebSocket error: {exc}", exc_info=True)
    finally:
        # Guarantee session buffer cleanup on disconnect
        session.clear()
