import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { useCameraLandmarks } from '../../hooks/useCameraLandmarks';

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

  const isRecordingRef = useRef(false);
  const framesBufferRef = useRef<Float32Array[]>([]);

  // Frame listener from shared 15 FPS pipeline
  const handleFrame = useCallback((landmarks: Float32Array) => {
    if (!isRecordingRef.current) return;

    framesBufferRef.current.push(new Float32Array(landmarks));
    if (framesBufferRef.current.length >= TOTAL_FRAMES) {
      isRecordingRef.current = false;
      setRecordedFrames([...framesBufferRef.current]);
      setRecordingState('review');
    }
  }, []);

  // Shared 15 FPS camera capture pipeline
  const {
    videoRef,
    canvasRef,
    cameraError,
    isCameraActive,
  } = useCameraLandmarks({
    enabled: true,
    showOverlay: true,
    onFrame: handleFrame,
  });

  // Load sample counts from backend
  const fetchCounts = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchCounts();
  }, [fetchCounts]);

  // Countdown & Recording Routine
  const startRecordingFlow = () => {
    if (!SIGNER_REGEX.test(signer)) {
      setErrorMessage('Signer ID must only contain lowercase letters, numbers, and underscores (^[a-z0-9_]+$).');
      return;
    }
    setErrorMessage(null);
    setStatusMessage(null);
    framesBufferRef.current = [];
    setRecordedFrames([]);
    setRecordingState('countdown');
    setCountdown(3);

    let count = 3;
    const countTimer = setInterval(() => {
      count -= 1;
      if (count > 0) {
        setCountdown(count);
      } else {
        clearInterval(countTimer);
        setRecordingState('recording');
        isRecordingRef.current = true;
      }
    }, 800);
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
    } catch (err: unknown) {
      const errDetail = err instanceof Error ? err.message : 'Error saving sample';
      setErrorMessage(errDetail);
    }
  };

  const handleRetry = () => {
    framesBufferRef.current = [];
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
              className="flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-2 text-xs font-bold text-ink hover:bg-surface min-h-[44px]"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              <span>Back to Workplace</span>
            </button>
            <div>
              <h1 className="font-serif text-xl font-bold text-ink">
                Landmark Data Recorder
              </h1>
              <p className="text-xs text-ink-muted">
                15 FPS Browser Skeletal Extraction (30 frames / 2.0s per sample)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-semibold">
            <div className="flex items-center gap-1.5 rounded-input border border-border bg-bg px-3 py-1.5">
              <Database className="h-4 w-4 text-accent" />
              <span>Total Dataset Samples:</span>
              <strong className="text-ink">{sampleCounts.total}</strong>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6 lg:flex-row">
        {/* Left: Camera Feed & Landmarks */}
        <div className="flex flex-1 flex-col">
          <div className="rounded-card border border-border bg-surface p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Camera className="h-5 w-5 text-accent" />
                <h2 className="font-serif text-lg font-bold text-ink">
                  Capture Preview (Mirrored View)
                </h2>
              </div>
              <span className="text-xs text-ink-muted">
                Raw coordinates are stored unmirrored (30, 225)
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
                  <span>RECORDING ({framesBufferRef.current.length}/{TOTAL_FRAMES})</span>
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

              <canvas
                ref={canvasRef}
                className="pointer-events-none absolute inset-0 h-full w-full object-cover -scale-x-100"
              />
            </div>

            {/* Error or Status Alert */}
            {(cameraError || errorMessage) && (
              <div className="mt-3 flex items-center gap-2 rounded-input border border-emergency bg-emergency-bg p-3 text-xs font-semibold text-emergency">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{cameraError || errorMessage}</span>
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
                  Existing samples: {currentCount}
                </span>
              </div>
              <select
                id="word-select"
                value={selectedWord}
                onChange={(e) => setSelectedWord(e.target.value)}
                className="w-full rounded-input border border-border bg-bg px-3 py-2 text-sm font-semibold text-ink focus-visible:outline-none min-h-[44px]"
              >
                {VOCAB_WORDS.map((w) => (
                  <option key={w} value={w}>
                    {w} ({sampleCounts.byWord[w] || 0} samples)
                  </option>
                ))}
              </select>
            </div>

            {/* Action Buttons */}
            {recordingState === 'idle' && (
              <button
                type="button"
                onClick={startRecordingFlow}
                disabled={!isCameraActive}
                className="w-full flex items-center justify-center gap-2 rounded-input bg-accent px-4 py-3 text-sm font-bold text-accent-ink hover:opacity-95 min-h-[48px] disabled:opacity-40"
              >
                <Play className="h-4 w-4" />
                <span>Start 3s Countdown & Record</span>
              </button>
            )}

            {recordingState === 'countdown' && (
              <div className="flex items-center justify-center rounded-input bg-bg py-3 text-sm font-bold text-warn min-h-[48px] border border-border">
                <span>Countdown in progress...</span>
              </div>
            )}

            {recordingState === 'recording' && (
              <div className="flex items-center justify-center rounded-input bg-emergency py-3 text-sm font-bold text-surface min-h-[48px] animate-pulse">
                <span>Sign {selectedWord.toUpperCase()} now!</span>
              </div>
            )}

            {recordingState === 'review' && (
              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  onClick={handleSave}
                  className="w-full flex items-center justify-center gap-2 rounded-input bg-ok px-4 py-3 text-sm font-bold text-surface hover:opacity-95 min-h-[48px]"
                >
                  <Save className="h-4 w-4" />
                  <span>Save Sample ({TOTAL_FRAMES} frames)</span>
                </button>
                <button
                  type="button"
                  onClick={handleRetry}
                  className="w-full flex items-center justify-center gap-2 rounded-input border border-border bg-bg px-4 py-2 text-xs font-semibold text-ink hover:bg-surface min-h-[40px]"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>Discard & Retry</span>
                </button>
              </div>
            )}
          </div>

          {/* Quick Guide Card */}
          <div className="rounded-card border border-border bg-surface p-4 text-xs text-ink-muted">
            <h3 className="font-serif font-bold text-ink mb-2 flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-accent" />
              Recording Rules
            </h3>
            <ul className="space-y-1 list-disc list-inside">
              <li>Position shoulders and upper body centered in the frame.</li>
              <li>Wait for countdown to reach 0 before starting the gesture.</li>
              <li>Missing hands stay strictly 0.0 (no interpolation).</li>
              <li>Saved as (30, 225) float32 in data/landmarks/&lt;signer&gt;/&lt;label&gt;/.</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
};
