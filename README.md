# SignBridge: Indian Sign Language (ISL) Assistive Communication System

SignBridge is a two-way assistive communication application designed for **hospital** and **bank** counters. It enables seamless interactions between Indian Sign Language (ISL) users and hearing staff.

---

## 1. System Architecture

* **Sign $\to$ Speech Pipeline (Signer $\to$ Staff)**:
  `Webcam` $\to$ `MediaPipe Holistic (Pose + 2 Hands)` $\to$ `Landmark Sequences (30 frames, 225 dims)` $\to$ `PyTorch Sequence Model (LSTM/GRU)` $\to$ `LLM Sentence Construction` $\to$ `Synthesized Speech / Captions (English, Hindi, Kannada)`.
* **Speech $\to$ Sign Pipeline (Staff $\to$ Signer)**:
  `Microphone` $\to$ `Whisper Speech-to-Text` $\to$ `Keyword / ISL Clip Retrieval` $\to$ `Synchronized Sign Video Playback`.
* **Privacy by Design**:
  Under no circumstances are raw video frames or photographs saved or logged. Only numeric landmark coordinates `(30, 225)` are captured and processed.

---

## 2. Monorepo Structure

```
SignBridge/
├── frontend/                     # React 19 + Vite + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/
│   │   │   ├── alerts/           # EmergencyBanner, ErrorBanner
│   │   │   ├── conversation/     # Timeline, SentenceConfirmation
│   │   │   ├── layout/           # Header, BottomBar, StateSwitcher
│   │   │   └── sign-to-speech/   # WebcamPreview, LiveCaptions
│   │   ├── types/                # Strict TypeScript interfaces
│   │   ├── App.tsx               # Primary two-pane workspace
│   │   └── index.css             # Design tokens & CSS variables
│   └── package.json
├── ml-service/                   # FastAPI + WebSockets + PyTorch backend
│   ├── app/
│   │   ├── main.py               # FastAPI entry point & CORS
│   │   ├── core/
│   │   │   ├── config.py         # Configuration settings
│   │   │   └── normalization.py  # Canonical landmark normalization
│   │   ├── ml/
│   │   │   └── architecture.py   # SignBridgeGRU model definition
│   │   ├── routes/
│   │   │   ├── health.py         # GET /health
│   │   │   ├── samples.py        # POST /samples, GET /samples/counts
│   │   │   └── websocket.py      # WS /ws/landmarks
│   │   └── schemas/protocol.py   # Pydantic v2 schemas
│   ├── data/landmarks/           # (.gitignored) 30-frame landmark sequences
│   ├── models/                   # (.gitignored) Trained .pt / .onnx weights
│   ├── scripts/
│   │   ├── collect_data.py       # MediaPipe Holistic webcam landmark recorder
│   │   ├── extract_landmarks.py  # Offline video landmark extraction
│   │   └── train.py              # Sequence model training
│   ├── tests/                    # Normalization parity test suite
│   └── requirements.txt
├── docs/
│   ├── DESIGN.md                 # Design system tokens and UI rules
│   ├── LANDMARKS.md              # Landmark coordinate spec, normalization, 15 FPS
│   └── vocabulary.md             # 42-word ISL vocabulary (Hospital & Bank)
├── rules.md                      # Monorepo coding conventions & privacy rules
└── README.md
```

---

## 3. Quick Start & Run Instructions

### Prerequisites
* **Node.js**: v20+ and npm / pnpm
* **Python**: v3.10+ (Anaconda / Virtualenv)
* **Webcam**: Standard USB or integrated webcam

---

### Running the ML / API Service (`ml-service`)

1. **Activate Python Virtual Environment**:
   ```powershell
   cd ml-service
   # On Windows:
   .\.venv\Scripts\Activate.ps1
   ```

2. **Start the FastAPI Server**:
   ```powershell
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Verify API Endpoints**:
   * Health endpoint: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   * Interactive Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * Live Landmark WebSocket: `ws://127.0.0.1:8000/ws/landmarks`

---

### Running the Frontend (`frontend`)

1. **Install Dependencies**:
   ```powershell
   cd frontend
   npm install
   ```

2. **Start Development Server**:
   ```powershell
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### Recording Landmark Training Data

Record 30-frame skeletal coordinate sequences into `ml-service/data/landmarks/<signer>/<label>/sample_XXXX.npy` at fixed 15 FPS:

```powershell
cd ml-service

# Record all 42 words (40 samples each):
python scripts/collect_data.py --signer signer_01 --samples 40

# Record specific medical/banking words:
python scripts/collect_data.py --signer signer_01 --words doctor,fever,medicine,account,emergency --samples 30

# Controls during recording:
#   [SPACE] : Trigger 3-second countdown and record 30 frames at 15 FPS
#   [s]     : Skip to next word
#   [q]     : Quit recording session
```

Alternatively, use the browser-based recorder at **[http://localhost:5173/record](http://localhost:5173/record)** (or click **Record Samples** in the header).

---

## 4. Live View & UI State Inspection

### Live Streaming Mode
* In the live workplace view, the browser streams landmark coordinate vectors `(225,)` to `/ws/landmarks` at **fixed 15 FPS**.
* The server maintains a rolling 30-frame buffer per connection and runs GRU inference every 3 frames with temporal smoothing (3 of 5 windows, confidence $\ge 0.80$) and repetition lock.
* If a model has not yet been trained or loaded, SignBridge operates in **Demo Mode**:
  * Displays a persistent amber banner: *"Demo mode: model not trained, predictions are not real"*.
  * Sentence confirmation and speech synthesis are locked to prevent synthetic or dummy words from entering the conversation.
* When emergency distress signs (`emergency`, `ambulance`) are recognized at $\ge 0.90$ confidence for 3 consecutive windows, the high-priority **Emergency Alert Banner** triggers instantly and is never suppressed by word repetition locks.

### Dev State Switcher
The interactive Design State Switcher allows inspecting all states from [docs/DESIGN.md](docs/DESIGN.md) (Empty, Camera Denied, Loading Model, Recognising, Low Confidence, Sentence Awaiting Speech, Error/Offline, Emergency, No Signer).
* **Toggle Shortcut**: Press **`Shift + D`** anywhere in the app to show or hide the Dev Inspector bar.
* **URL Parameter**: Append `?dev=true` to the URL.

---

## 5. Verification & Test Commands

### Run Backend Inference & Quality Tests
```powershell
# 1. Parity normalization test (verifies identical math with TypeScript)
.\ml-service\.venv\python.exe ml-service/tests/test_normalization_parity.py

# 2. Live inference test suite (smoothing, emergency persistence, rate limits, buffer isolation)
.\ml-service\.venv\python.exe ml-service/tests/test_live_inference.py

# 3. Model training pipeline tests (data splits, augmentation, class balancing)
.\ml-service\.venv\python.exe ml-service/tests/test_train.py

# 4. Dataset audit & readiness checks
.\ml-service\.venv\python.exe ml-service/tests/test_check_data.py
```
