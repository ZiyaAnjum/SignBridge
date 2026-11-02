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

## 4. UI States Preview Switcher

The frontend includes an interactive **Design State Switcher** bar at the top to preview and inspect all 8 required states from [docs/DESIGN.md](docs/DESIGN.md):
1. **Empty**: No conversation yet, clean one-line instructions.
2. **Camera Denied**: Accessible guidance with explanation of privacy and browser permission steps.
3. **Loading Model**: Spinner and initialization status message.
4. **Recognising**: Signer detected, pulsating status badge, and live landmark overlay.
5. **Low Confidence**: *"Not sure. Please sign again"* prompt displaying top 2 alternative candidate matches.
6. **Sentence Awaiting Speech**: Built sentence preview with accessible **Confirm & Speak** and **Fix** actions.
7. **Error / Connection Lost**: Offline status warning with manual retry.
8. **Emergency**: High-priority full-width banner with staff dispatch and dismiss actions.
