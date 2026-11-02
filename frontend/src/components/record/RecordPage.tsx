import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  Play,
  RotateCcw,
  Save,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Database,
  Layers,
} from 'lucide-react';
import { initializeMediaPipe, extractLandmarksFromVideo } from '../../lib/mediapipe';
import { normalizeSequence } from '../../lib/normalization';

interface RecordPageProps {
  onBackToApp: () => void;
}

const VOCAB_WORDS = [
  'idle',
  'yes', 'no', 'help', 'please', 'thank_you', 'sorry', 'repeat', 'understand', 'wait', 'i', 'you', 'water',
  'today', 'tomorrow', 'emergency', 'ambulance', 'pain', 'blood',
  'doctor', 'nurse', 'hospital', 'medicine', 'fever', 'cough', 'head', 'stomach', 'chest', 'injection', 'appointment', 'test', 'allergy',
  'bank', 'money', 'account', 'card', 'cash', 'loan', 'form', 'signature', 'deposit', 'withdraw', 'balance'
];

const SIGNER_REGEX = /^[a-z0-9_]+$/;
const TARGET_FPS = 15;
const FRAME_INTERVAL_MS = 1000 / TARGET_FPS; // 66.67ms
const TOTAL_FRAMES = 30;

export const RecordPage: React.FC<RecordPageProps> = ({ onBackToApp }) => {
  const [signer, setSigner] = useState('signer_01');
  const [selectedWord, setSelectedWord] = useState('idle');
  const [sampleCounts, setSampleCounts] = useState<{ total: number; byWord: Record<string, number> }>({
    total: 0,
    byWord: {},
  });

  const [recordingState, setRecordingState] = useState<'idle' | 'countdown' | 'recording' | 'review'>('idle');
  const [countdown, setCountdown] = useState(3);
  const [recordedFrames, setRecordedFrames] = useState<Float32Array[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recordingRef = useRef(false);

  // Load sample counts from backend
  const fetchCounts = async () => {
    try {
      const res = await fetch('http://localhost:8000/samples/counts');
      if (res.ok) {
        const data = await res.json();
        setSampleCounts({
          total: data.total_samples || 0,
          byWord: data.by_word || {},
        });
      }
    } catch {
      // Backend may be offline
    }
  };

  useEffect(() => {
    fetchCounts();
    initializeMediaPipe();

    let stream: MediaStream | null = null;
    navigator.mediaDevices?.getUserMedia({ video: { width: 1280, height: 720 } })
      .then((s) => {
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch((err) => {
        setErrorMessage('Camera access denied or unavailable: ' + err.message);
      });

    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // Countdown & Recording Routine
  const startRecordingFlow = () => {
    if (!SIGNER_REGEX.test(signer)) {
      setErrorMessage('Signer ID must only contain lowercase letters, numbers, and underscores (^[a-z0-9_]+$).');
      return;
    }
    setErrorMessage(null);
    setStatusMessage(null);
    setRecordingState('countdown');
    setCountdown(3);

    let count = 3;
    const countTimer = setInterval(() => {
      count -= 1;
      if (count > 0) {
        setCountdown(count);
      } else {
        clearInterval(countTimer);
        runCapture();
      }
    }, 800);
  };

  const runCapture = () => {
    setRecordingState('recording');
    recordingRef.current = true;
    const frames: Float32Array[] = [];
    let lastTimestamp = 0;

    const captureLoop = () => {
      if (!recordingRef.current) return;
      const now = performance.now();

      if (now - lastTimestamp >= FRAME_INTERVAL_MS) {
        lastTimestamp = now;
        if (videoRef.current) {
          const frameLandmarks = extractLandmarksFromVideo(videoRef.current, now);
          frames.push(frameLandmarks);
        }
      }

      if (frames.length < TOTAL_FRAMES) {
        requestAnimationFrame(captureLoop);
      } else {
        recordingRef.current = false;
        setRecordedFrames(frames);
        setRecordingState('review');
      }
    };

    requestAnimationFrame(captureLoop);
  };

  const handleSave = async () => {
    if (recordedFrames.length !== TOTAL_FRAMES) return;

    try {
      setStatusMessage('Saving sample to backend...');
      // Convert Float32Array sequence to regular array
      const serializableFrames = recordedFrames.map((f) => Array.from(f));

      const res = await fetch('http://localhost:8000/samples', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signer: signer.trim(),
          label: selectedWord,
          landmarks: serializableFrames,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save sample');
      }

      const data = await res.json();
      setStatusMessage(`Saved ${data.filename}! Total for ${selectedWord}: ${data.word_total}`);
      setRecordingState('idle');
      setRecordedFrames([]);
      fetchCounts();
    } catch (err: any) {
      setErrorMessage(err.message || 'Error saving sample');
    }
  };

  const handleRetry = () => {
    setRecordedFrames([]);
    setRecordingState('idle');
    setErrorMessage(null);
    setStatusMessage(null);
  };

  const currentCount = sampleCounts.byWord[selectedWord] || 0;

  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col">
      {/* Header Bar */}
      <header className="border-b border-border bg-surface px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={onBackToApp}
              className="flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-2 text-xs font-bold text-ink hover:bg-surface"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Back to Workplace</span>
            </button>
            <div>
              <h1 className="font-serif text-xl font-bold text-ink">
                Landmark Data Recorder
              </h1>
              <p className="font-sans text-xs text-ink-muted">
                Record 30-frame ISL coordinate sequences at 15 FPS (no video stored)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-1.5 text-xs font-semibold text-ink">
              <Database className="h-4 w-4 text-accent" aria-hidden="true" />
              <span>Total Dataset: {sampleCounts.total} samples</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6 lg:flex-row">
        {/* Left: Video Preview & Recording Canvas */}
        <div className="flex flex-1 flex-col">
          <div className="rounded-card border border-border bg-surface p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="font-sans text-xs font-bold uppercase tracking-wider text-ink-muted">
                Camera Feed (Display mirrored, coordinates unmirrored)
              </span>
              <span className="text-xs text-accent font-semibold">
                15 FPS · 30 frames
              </span>
            </div>

            <div className="relative aspect-video w-full overflow-hidden rounded-input border border-border bg-ink">
              {/* Countdown Overlay */}
              {recordingState === 'countdown' && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-ink/70 text-surface">
                  <span className="font-serif text-6xl font-bold text-warn">
                    {countdown}
                  </span>
                  <p className="mt-2 text-sm font-semibold">Get Ready...</p>
                </div>
              )}

              {/* Recording Progress Indicator */}
              {recordingState === 'recording' && (
                <div className="absolute top-4 left-4 z-20 flex items-center gap-2 rounded-input bg-emergency px-3 py-1.5 text-xs font-bold text-surface">
                  <span className="h-2 w-2 rounded-full bg-surface animate-ping" />
                  <span>RECORDING ({recordedFrames.length}/{TOTAL_FRAMES})</span>
                </div>
              )}

              {/* Review Overlay */}
              {recordingState === 'review' && (
                <div className="absolute top-4 left-4 z-20 rounded-input border border-border bg-surface/90 px-3 py-1.5 text-xs font-bold text-ink">
                  Sequence Captured (30 frames)
                </div>
              )}

              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="h-full w-full object-cover -scale-x-100"
              />
            </div>

            {/* Error or Status Alert */}
            {errorMessage && (
              <div className="mt-3 flex items-center gap-2 rounded-input border border-emergency bg-emergency-bg p-3 text-xs font-semibold text-emergency">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {statusMessage && (
              <div className="mt-3 flex items-center gap-2 rounded-input border border-ok bg-surface p-3 text-xs font-semibold text-ok">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{statusMessage}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Controls & Word Selection */}
        <div className="flex w-full lg:w-96 flex-col gap-4">
          <div className="rounded-card border border-border bg-surface p-5">
            <h2 className="font-serif text-lg font-bold text-ink mb-4">
              Recording Controls
            </h2>

            {/* Signer ID Input */}
            <div className="mb-4">
              <label htmlFor="signer-input" className="block text-xs font-bold text-ink uppercase tracking-wider mb-1">
                Signer ID (^[a-z0-9_]+$)
              </label>
              <input
                id="signer-input"
                type="text"
                value={signer}
                onChange={(e) => setSigner(e.target.value.toLowerCase())}
                placeholder="e.g. signer_01"
                className="w-full rounded-input border border-border bg-bg px-3 py-2 text-sm text-ink focus-visible:outline-none min-h-[44px]"
              />
            </div>

            {/* Word Selection */}
            <div className="mb-5">
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="word-select" className="block text-xs font-bold text-ink uppercase tracking-wider">
                  Target Word / Class
                </label>
                <span className="text-xs font-bold text-accent">
                  {currentCount} samples recorded
                </span>
              </div>

              <select
                id="word-select"
                value={selectedWord}
                onChange={(e) => setSelectedWord(e.target.value)}
                className="w-full rounded-input border border-border bg-bg px-3 py-2.5 text-sm font-semibold text-ink cursor-pointer focus-visible:outline-none min-h-[44px]"
              >
                {VOCAB_WORDS.map((w) => (
                  <option key={w} value={w}>
                    {w.toUpperCase()} {sampleCounts.byWord[w] ? `(${sampleCounts.byWord[w]} recorded)` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Action Buttons */}
            {recordingState === 'idle' && (
              <button
                type="button"
                onClick={startRecordingFlow}
                className="w-full flex items-center justify-center gap-2 rounded-input bg-accent px-4 py-3 text-sm font-bold text-accent-ink hover:opacity-95 min-h-[48px]"
              >
                <Play className="h-4 w-4" />
                <span>Start Recording ({selectedWord.toUpperCase()})</span>
              </button>
            )}

            {recordingState === 'review' && (
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleSave}
                  className="w-full flex items-center justify-center gap-2 rounded-input bg-accent px-4 py-3 text-sm font-bold text-accent-ink hover:opacity-95 min-h-[48px]"
                >
                  <Save className="h-4 w-4" />
                  <span>Save Sample ({selectedWord})</span>
                </button>

                <button
                  type="button"
                  onClick={handleRetry}
                  className="w-full flex items-center justify-center gap-2 rounded-input border border-border bg-surface px-4 py-3 text-sm font-semibold text-ink hover:bg-bg min-h-[48px]"
                >
                  <RotateCcw className="h-4 w-4 text-ink-muted" />
                  <span>Discard & Retry</span>
                </button>
              </div>
            )}
          </div>

          {/* Guidelines Box */}
          <div className="rounded-card border border-border bg-surface p-4 text-xs text-ink-muted space-y-2">
            <h3 className="font-serif text-sm font-bold text-ink">
              Data Collection Protocol
            </h3>
            <p>1. Target 40+ samples per class across at least 5 signers.</p>
            <p>2. Keep signer ID consistent per person to allow train/val/test splits strictly by signer.</p>
            <p>3. Use <strong className="text-ink">idle</strong> to record neutral resting poses and transition gestures.</p>
          </div>
        </div>
      </main>
    </div>
  );
};

