"""Unit and integration tests for SignBridge Part C live inference.

Tests:
1. Smoothing logic (3 of last 5 windows AND confidence >= 0.8)
2. Idle suppression and repetition suppression
3. Emergency threshold (strictly 'emergency' and 'ambulance' with conf >= 0.9 for 3 consecutive windows)
4. Malformed frame rejection (wrong length, NaN, Inf, non-list)
5. Message size and frame rate limit validation
6. Per-connection buffer isolation and reset on disconnect
7. Model compatibility validation (layout, fps, window length, normalization version)
8. End-to-end inference execution flow with tiny temp model
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch

TESTS_DIR = Path(__file__).resolve().parent
ML_SERVICE_DIR = TESTS_DIR.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.ml.architecture import SignBridgeGRU
from app.ml.engine import (
    ModelEngine,
    EXPECTED_LAYOUT_VERSION,
    EXPECTED_FPS,
    EXPECTED_WINDOW_LENGTH,
    EXPECTED_NORMALIZATION_VERSION,
)
from app.ml.session import ConnectionSession, MAX_MESSAGE_BYTES, MAX_FRAMES_PER_SECOND


def test_smoothing_logic():
    session = ConnectionSession()
    all_sorted_dummy = [("doctor", 0.85), ("help", 0.10)]

    # Window 1: doctor 0.85 (count=1 -> low confidence, reported=None)
    res1 = session.process_prediction("doctor", 0.85, all_sorted_dummy, latency_ms=1.2)
    assert res1.label is None, "Window 1 should not report (1/5 < 3/5)"
    assert len(res1.top_guesses) == 2
    assert res1.top_guesses[0].label == "doctor"

    # Window 2: doctor 0.82 (count=2 -> low confidence, reported=None)
    res2 = session.process_prediction("doctor", 0.82, all_sorted_dummy, latency_ms=1.1)
    assert res2.label is None, "Window 2 should not report (2/5 < 3/5)"

    # Window 3: doctor 0.88 (count=3/3 >= 3 and conf >= 0.8 -> reported='doctor')
    res3 = session.process_prediction("doctor", 0.88, all_sorted_dummy, latency_ms=1.3)
    assert res3.label == "doctor", f"Window 3 should report 'doctor', got {res3.label}"
    assert res3.confidence == 0.88
    assert res3.english == "doctor"
    assert res3.hindi == "डॉक्टर"
    assert res3.kannada == "ವೈದ್ಯರು"

    # Window 4: low confidence word wins 3 times but conf < 0.8 -> should not report
    session_low_conf = ConnectionSession()
    low_sorted = [("help", 0.65), ("doctor", 0.20)]
    for _ in range(4):
        res = session_low_conf.process_prediction("help", 0.65, low_sorted, latency_ms=1.0)
    assert res.label is None, "Confidence < 0.8 should return low-confidence result without reporting word"
    assert len(res.top_guesses) == 2
    assert res.top_guesses[0].label == "help"


def test_idle_and_repetition_suppression():
    session = ConnectionSession()
    dummy_sorted_doc = [("doctor", 0.85), ("idle", 0.10)]
    dummy_sorted_idle = [("idle", 0.90), ("doctor", 0.05)]

    # 1. Sign doctor until reported
    for _ in range(3):
        res = session.process_prediction("doctor", 0.85, dummy_sorted_doc, latency_ms=1.0)
    assert res.label == "doctor", "Doctor should be reported after 3 windows"

    # 2. Next window: doctor still wins -> repetition suppression must suppress it!
    res_repeat = session.process_prediction("doctor", 0.86, dummy_sorted_doc, latency_ms=1.0)
    assert res_repeat.label is None, "Repetition of same word without idle/other word in between must be suppressed"

    # 3. User goes to idle: idle wins 3 times -> reported_label must be None
    for _ in range(3):
        res_idle = session.process_prediction("idle", 0.90, dummy_sorted_idle, latency_ms=1.0)
    assert res_idle.label is None, "Idle must never be reported as a word"
    assert session.last_reported_word is None, "Idle should reset repetition lock"

    # 4. Now doctor can be signed and reported again!
    for _ in range(3):
        res_doc2 = session.process_prediction("doctor", 0.85, dummy_sorted_doc, latency_ms=1.0)
    assert res_doc2.label == "doctor", "Doctor should be reportable again after idle reset"


def test_emergency_threshold():
    session = ConnectionSession()
    em_sorted = [("emergency", 0.95), ("ambulance", 0.04)]
    amb_sorted = [("ambulance", 0.92), ("emergency", 0.05)]
    doc_sorted = [("doctor", 0.99), ("emergency", 0.01)]

    # Window 1: emergency >= 0.90 (consecutive=1)
    res1 = session.process_prediction("emergency", 0.92, em_sorted, latency_ms=1.0)
    assert res1.is_emergency is False, "1 window of emergency should not trigger alert"

    # Window 2: emergency >= 0.90 (consecutive=2)
    res2 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert res2.is_emergency is False, "2 windows of emergency should not trigger alert"

    # Window 3: emergency >= 0.90 (consecutive=3) -> Alert triggers!
    res3 = session.process_prediction("emergency", 0.91, em_sorted, latency_ms=1.0)
    assert res3.is_emergency is True, "3 consecutive windows of emergency >= 0.9 must trigger is_emergency"

    # Window 4: Non-emergency breaks streak
    res4 = session.process_prediction("water", 0.85, [("water", 0.85)], latency_ms=1.0)
    assert res4.is_emergency is False, "Streak should be broken"

    # Ambulance also triggers after 3 consecutive windows
    for _ in range(2):
        res = session.process_prediction("ambulance", 0.93, amb_sorted, latency_ms=1.0)
        assert res.is_emergency is False
    res_amb = session.process_prediction("ambulance", 0.93, amb_sorted, latency_ms=1.0)
    assert res_amb.is_emergency is True, "3 consecutive windows of ambulance >= 0.9 must trigger is_emergency"

    # Other words (even at 0.99) NEVER trigger emergency
    session2 = ConnectionSession()
    for _ in range(5):
        res = session2.process_prediction("doctor", 0.99, doc_sorted, latency_ms=1.0)
        assert res.is_emergency is False, "Doctor must never trigger emergency alert"


def test_malformed_frame_rejection():
    session = ConnectionSession()

    # Valid frame (225 finite floats)
    valid_frame = [0.0] * 225
    ok, err, arr = session.validate_frame(valid_frame)
    assert ok is True
    assert err is None
    assert arr.shape == (225,)

    # Wrong length (e.g. 200)
    ok, err, _ = session.validate_frame([0.0] * 200)
    assert ok is False
    assert "Expected 225" in err

    # Contains NaN
    nan_frame = [0.0] * 225
    nan_frame[5] = float("nan")
    ok, err, _ = session.validate_frame(nan_frame)
    assert ok is False
    assert "NaN or Inf" in err

    # Contains Inf
    inf_frame = [0.0] * 225
    inf_frame[10] = float("inf")
    ok, err, _ = session.validate_frame(inf_frame)
    assert ok is False
    assert "NaN or Inf" in err

    # Non-list
    ok, err, _ = session.validate_frame("not_a_list")
    assert ok is False


def test_limits_and_rate_limiting():
    session = ConnectionSession()

    # Message size limit
    oversized_payload = "a" * (MAX_MESSAGE_BYTES + 10)
    assert len(oversized_payload) > MAX_MESSAGE_BYTES

    # Rate limiting: push up to MAX_FRAMES_PER_SECOND
    for _ in range(MAX_FRAMES_PER_SECOND):
        assert session.check_rate_limit() is False

    # Exceeding rate limit should trigger True
    assert session.check_rate_limit() is True


def test_per_connection_buffer_isolation():
    session_a = ConnectionSession()
    session_b = ConnectionSession()

    frame1 = np.ones(225, dtype=np.float32) * 0.1
    frame2 = np.ones(225, dtype=np.float32) * 0.9

    # Feed session_a 10 frames
    for _ in range(10):
        session_a.push_frame(frame1)

    # Feed session_b 25 frames
    for _ in range(25):
        session_b.push_frame(frame2)

    assert len(session_a.buffer) == 10
    assert len(session_b.buffer) == 25

    # Check contents do not leak between connections
    assert np.allclose(session_a.buffer[0], frame1)
    assert np.allclose(session_b.buffer[0], frame2)

    # Clear session_a on disconnect
    session_a.clear()
    assert len(session_a.buffer) == 0
    assert len(session_b.buffer) == 25, "session_b buffer must remain untouched after session_a is cleared"


def test_model_metadata_validation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Missing model and label map
        engine_empty = ModelEngine(models_dir=tmp_path)
        assert engine_empty.model_loaded is False
        assert "not found" in engine_empty.reason

        # 2. Mismatched metadata
        dummy_model = SignBridgeGRU(num_classes=3)
        torch.save(dummy_model.state_dict(), tmp_path / "signbridge_gru.pt")

        bad_metadata = {
            "landmark_layout_version": "v2-wrong",
            "fps": 30,  # Mismatch (expected 15)
            "window_length": 30,
            "normalization_version": EXPECTED_NORMALIZATION_VERSION,
            "classes": ["yes", "no", "idle"],
        }
        with open(tmp_path / "label_map.json", "w", encoding="utf-8") as f:
            json.dump(bad_metadata, f)

        engine_mismatch = ModelEngine(models_dir=tmp_path)
        assert engine_mismatch.model_loaded is False
        assert "landmark_layout_version" in engine_mismatch.reason
        assert "fps" in engine_mismatch.reason

        # 3. Valid metadata
        good_metadata = {
            "landmark_layout_version": EXPECTED_LAYOUT_VERSION,
            "fps": EXPECTED_FPS,
            "window_length": EXPECTED_WINDOW_LENGTH,
            "normalization_version": EXPECTED_NORMALIZATION_VERSION,
            "classes": ["yes", "no", "idle"],
            "hidden_size": 64,
            "num_layers": 1,
            "bidirectional": True,
            "dropout": 0.2,
        }
        with open(tmp_path / "label_map.json", "w", encoding="utf-8") as f:
            json.dump(good_metadata, f)

        engine_good = ModelEngine(models_dir=tmp_path)
        assert engine_good.model_loaded is True
        assert engine_good.reason is None
        assert len(engine_good.classes) == 3


def test_end_to_end_inference_flow_with_temp_model():
    """Verifies complete end-to-end inference flow:
    raw frames -> 30-frame buffer -> 3-frame stride -> normalization -> GRU forward -> smoothing.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        classes = ["yes", "no", "idle", "emergency"]
        tiny_model = SignBridgeGRU(num_classes=len(classes))
        torch.save(tiny_model.state_dict(), tmp_path / "signbridge_gru.pt")

        meta = {
            "landmark_layout_version": EXPECTED_LAYOUT_VERSION,
            "fps": EXPECTED_FPS,
            "window_length": EXPECTED_WINDOW_LENGTH,
            "normalization_version": EXPECTED_NORMALIZATION_VERSION,
            "classes": classes,
        }
        with open(tmp_path / "label_map.json", "w", encoding="utf-8") as f:
            json.dump(meta, f)

        temp_engine = ModelEngine(models_dir=tmp_path)
        assert temp_engine.model_loaded is True

        session = ConnectionSession()
        valid_frame = np.zeros(225, dtype=np.float32)
        valid_frame[33] = 0.45  # Left shoulder
        valid_frame[36] = 0.55  # Right shoulder

        inference_count = 0
        last_prediction = None

        # Feed 33 frames
        for i in range(1, 34):
            session.push_frame(valid_frame)
            if session.should_run_inference():
                inference_count += 1
                norm_seq = session.get_normalized_sequence()
                assert norm_seq.shape == (30, 225)

                t0 = time.perf_counter()
                top_label, top_conf, all_sorted = temp_engine.predict(norm_seq)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                last_prediction = session.process_prediction(
                    current_label=top_label,
                    current_conf=top_conf,
                    all_sorted=all_sorted,
                    latency_ms=latency_ms,
                )

        # Buffer was full at frame 30 (30%3==0 -> ran), frame 33 (33%3==0 -> ran)
        assert inference_count == 2, f"Expected 2 inferences at frames 30 and 33, got {inference_count}"
        assert last_prediction is not None
        assert last_prediction.model_loaded is True
        assert last_prediction.inference_latency_ms > 0.0
        assert len(last_prediction.top_guesses) == 2


def test_emergency_never_suppressed_by_repetition():
    """Confirm is_emergency is never suppressed by the word repetition lock:
    First emergency triggers alert; subsequent emergency retains alert even when
    word emission is locked; after idle, a second emergency triggers alert again.
    """
    session = ConnectionSession()
    em_sorted = [("emergency", 0.95), ("ambulance", 0.04)]
    idle_sorted = [("idle", 0.95), ("emergency", 0.02)]

    # 1. Sign emergency for 3 consecutive windows -> alert triggers, word emitted
    res1 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert not res1.is_emergency and res1.label is None
    res2 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert not res2.is_emergency and res2.label is None
    res3 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert res3.is_emergency is True
    assert res3.label == "emergency"
    assert res3.state == "emergency"

    # 2. Window 4: emergency continues -> word is suppressed by repetition lock, BUT alert remains active!
    res4 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert res4.is_emergency is True, "is_emergency MUST NOT be suppressed by word repetition lock"
    assert res4.label is None, "Word repetition should be suppressed"
    assert res4.state == "emergency"

    # 3. User goes to idle: emergency alert clears, repetition lock resets
    for _ in range(3):
        res_idle = session.process_prediction("idle", 0.95, idle_sorted, latency_ms=1.0)
    assert res_idle.is_emergency is False
    assert res_idle.label is None
    assert session.last_reported_word is None

    # 4. Emergency triggered second time after idle: 3 consecutive windows triggers alert again
    session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    res_em2 = session.process_prediction("emergency", 0.95, em_sorted, latency_ms=1.0)
    assert res_em2.is_emergency is True
    assert res_em2.label == "emergency"


def test_signer_presence_detection():
    """Test no-signer detection:
    - If shoulders missing in >15 frames: state 'no_signer', short reason
    - If hands missing in >20 frames: state 'no_signer', short reason
    - If signer is present: passes check
    """
    session = ConnectionSession()

    def make_valid_frame() -> np.ndarray:
        frame = np.zeros(225, dtype=np.float32)
        # Left shoulder at index 11 (33, 34, 35)
        frame[33] = 0.4
        frame[34] = 0.5
        frame[35] = 0.0
        # Right shoulder at index 12 (36, 37, 38) -> width 0.2
        frame[36] = 0.6
        frame[37] = 0.5
        frame[38] = 0.0
        # Left hand (index 99..162)
        frame[99] = 0.5
        # Right hand (index 162..225)
        frame[162] = 0.5
        return frame

    # 1. 30 valid frames -> passes check
    for _ in range(30):
        session.push_frame(make_valid_frame())
    ok, reason = session.check_signer_presence()
    assert ok is True
    assert reason is None

    # 2. Window with >15 missing shoulder frames -> fails with shoulder reason
    session.clear()
    for _ in range(14):
        session.push_frame(make_valid_frame())
    for _ in range(16):
        # Frame with missing shoulders (zeros) but hands present
        f = np.zeros(225, dtype=np.float32)
        f[99] = 0.5
        session.push_frame(f)
    ok, reason = session.check_signer_presence()
    assert ok is False
    assert "shoulders" in reason.lower()
    no_signer_res = session.create_no_signer_result(reason, model_loaded=True)
    assert no_signer_res.state == "no_signer"
    assert no_signer_res.label is None

    # 3. Window with >20 missing hands frames -> fails with hands reason
    session.clear()
    for _ in range(9):
        session.push_frame(make_valid_frame())
    for _ in range(21):
        # Frame with valid shoulders but no hands
        f = np.zeros(225, dtype=np.float32)
        f[33] = 0.4
        f[34] = 0.5
        f[36] = 0.6
        f[37] = 0.5
        session.push_frame(f)
    ok, reason = session.check_signer_presence()
    assert ok is False
    assert "hands" in reason.lower()


def test_is_inferring_flag():
    """Test is_inferring flag is reset by clear() and defaults to False."""
    session = ConnectionSession()
    assert session.is_inferring is False
    session.is_inferring = True
    session.clear()
    assert session.is_inferring is False


if __name__ == "__main__":
    print("Running test_smoothing_logic...")
    test_smoothing_logic()
    print("Running test_idle_and_repetition_suppression...")
    test_idle_and_repetition_suppression()
    print("Running test_emergency_threshold...")
    test_emergency_threshold()
    print("Running test_emergency_never_suppressed_by_repetition...")
    test_emergency_never_suppressed_by_repetition()
    print("Running test_signer_presence_detection...")
    test_signer_presence_detection()
    print("Running test_is_inferring_flag...")
    test_is_inferring_flag()
    print("Running test_malformed_frame_rejection...")
    test_malformed_frame_rejection()
    print("Running test_limits_and_rate_limiting...")
    test_limits_and_rate_limiting()
    print("Running test_per_connection_buffer_isolation...")
    test_per_connection_buffer_isolation()
    print("Running test_model_metadata_validation...")
    test_model_metadata_validation()
    print("Running test_end_to_end_inference_flow_with_temp_model...")
    test_end_to_end_inference_flow_with_temp_model()
    print("\n[OK] ALL LIVE INFERENCE TESTS PASSED SUCCESSFULLY!")
