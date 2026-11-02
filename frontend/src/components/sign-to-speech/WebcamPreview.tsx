import React, { useState, useRef, useEffect } from 'react';
import { Camera, CameraOff, RefreshCw, Eye, EyeOff, Loader2 } from 'lucide-react';
import { UIState } from '../../types';

interface WebcamPreviewProps {
  uiState: UIState;
  onRetryCamera: () => void;
}

export const WebcamPreview: React.FC<WebcamPreviewProps> = ({
  uiState,
  onRetryCamera,
}) => {
  const [showLandmarks, setShowLandmarks] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  // Attempt real camera stream if available, fallback gracefully
  useEffect(() => {
    if (uiState === 'camera_denied' || uiState === 'loading_model' || uiState === 'error') {
      return;
    }

    let stream: MediaStream | null = null;
    navigator.mediaDevices?.getUserMedia({ video: { width: 1280, height: 720 } })
      .then((s) => {
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      })
      .catch(() => {
        // Handled via UI state
      });

    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [uiState]);

  return (
    <section
      className="flex flex-col rounded-card border border-border bg-surface p-4"
      aria-label="Signer camera preview and tracking"
    >
      {/* Header with Landmark Overlay Toggle */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Camera className="h-5 w-5 text-accent" aria-hidden="true" />
          <h2 className="font-serif text-lg font-bold text-ink">Signer Video</h2>
        </div>

        <button
          type="button"
          onClick={() => setShowLandmarks((prev) => !prev)}
          className="flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-1.5 text-xs font-semibold text-ink hover:bg-surface min-h-[36px]"
          aria-pressed={showLandmarks}
        >
          {showLandmarks ? (
            <>
              <Eye className="h-4 w-4 text-accent" aria-hidden="true" />
              <span>Landmarks: ON</span>
            </>
          ) : (
            <>
              <EyeOff className="h-4 w-4 text-ink-muted" aria-hidden="true" />
              <span>Landmarks: OFF</span>
            </>
          )}
        </button>
      </div>

      {/* 16:9 Video Aspect Container */}
      <div className="relative aspect-video w-full overflow-hidden rounded-input border border-border bg-ink">
        {/* State 2: Camera Permission Denied */}
        {uiState === 'camera_denied' && (
          <div
            className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-surface p-6 text-center"
            role="alert"
          >
            <div className="mb-4 rounded-full bg-emergency-bg p-4 text-emergency">
              <CameraOff className="h-8 w-8" aria-hidden="true" />
            </div>
            <h3 className="font-serif text-lg font-bold text-ink">
              Camera access blocked
            </h3>
            <p className="mt-2 max-w-md text-sm text-ink-muted leading-relaxed">
              SignBridge processes skeletal landmark coordinates locally to recognize Indian Sign Language.
              No video frames are recorded or saved to disk.
            </p>
            <p className="mt-2 text-xs font-semibold text-ink">
              Please click the camera icon in your browser address bar and choose &ldquo;Allow&rdquo;.
            </p>
            <button
              type="button"
              onClick={onRetryCamera}
              className="mt-4 flex items-center gap-2 rounded-input bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink hover:opacity-95 min-h-[48px]"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              <span>Retry Camera Access</span>
            </button>
          </div>
        )}

        {/* State 3: Loading Model */}
        {uiState === 'loading_model' && (
          <div
            className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-surface p-6 text-center"
            role="status"
          >
            <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden="true" />
            <h3 className="mt-4 font-serif text-lg font-bold text-ink">
              Loading recognition model
            </h3>
            <p className="mt-2 text-sm text-ink-muted">
              Initializing MediaPipe Holistic and ISL sequence weights...
            </p>
          </div>
        )}

        {/* Normal Video Feed */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover -scale-x-100"
        />

        {/* State 4: Recognising Indicator */}
        {uiState === 'recognising' && (
          <div
            className="absolute top-4 left-4 z-10 flex items-center gap-2 rounded-input border border-border bg-surface px-3 py-1.5 text-xs font-bold text-accent shadow-sm"
            role="status"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent"></span>
            </span>
            <span>Signer detected · Sign in progress...</span>
          </div>
        )}

        {/* Landmark Mesh Overlay Simulation (if active) */}
        {showLandmarks && uiState !== 'camera_denied' && uiState !== 'loading_model' && (
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 640 360"
            aria-hidden="true"
          >
            {/* Skeletal Pose guide nodes */}
            <circle cx="320" cy="110" r="4" fill="#0E6B63" />
            <circle cx="280" cy="160" r="4" fill="#0E6B63" />
            <circle cx="360" cy="160" r="4" fill="#0E6B63" />
            <circle cx="240" cy="220" r="4" fill="#0E6B63" />
            <circle cx="400" cy="220" r="4" fill="#0E6B63" />
            <line x1="280" y1="160" x2="360" y2="160" stroke="#0E6B63" strokeWidth="2" strokeDasharray="3 3" />
            <line x1="280" y1="160" x2="240" y2="220" stroke="#0E6B63" strokeWidth="2" />
            <line x1="360" y1="160" x2="400" y2="220" stroke="#0E6B63" strokeWidth="2" />
            {/* Left Hand Landmarks cluster */}
            <g transform="translate(210, 220)">
              <circle cx="10" cy="10" r="3" fill="#2E7D32" />
              <circle cx="20" cy="5" r="3" fill="#2E7D32" />
              <circle cx="30" cy="12" r="3" fill="#2E7D32" />
              <line x1="10" y1="10" x2="20" y2="5" stroke="#2E7D32" strokeWidth="1.5" />
            </g>
            {/* Right Hand Landmarks cluster */}
            <g transform="translate(390, 220)">
              <circle cx="10" cy="10" r="3" fill="#2E7D32" />
              <circle cx="20" cy="5" r="3" fill="#2E7D32" />
              <circle cx="30" cy="12" r="3" fill="#2E7D32" />
              <line x1="10" y1="10" x2="20" y2="5" stroke="#2E7D32" strokeWidth="1.5" />
            </g>
          </svg>
        )}

        {/* Subtitle helper in idle state */}
        {uiState === 'empty' && (
          <div className="absolute bottom-3 inset-x-4 z-10 rounded-input bg-surface/90 px-3 py-2 text-center text-xs font-semibold text-ink border border-border">
            Ready. Ask the signer to position hands inside the frame.
          </div>
        )}
      </div>
    </section>
  );
};

