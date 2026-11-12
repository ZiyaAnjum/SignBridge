import React from 'react';
import { Camera, CameraOff, RefreshCw, Eye, EyeOff, Loader2, UserX } from 'lucide-react';
import { UIState } from '../../types';

interface WebcamPreviewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef?: React.RefObject<HTMLCanvasElement | null>;
  uiState: UIState;
  showLandmarks: boolean;
  onToggleLandmarks: () => void;
  onRetryCamera: () => void;
  signerNotice?: string | null;
}

export const WebcamPreview: React.FC<WebcamPreviewProps> = ({
  videoRef,
  canvasRef,
  uiState,
  showLandmarks,
  onToggleLandmarks,
  onRetryCamera,
  signerNotice,
}) => {
  const isNoSigner = uiState === 'no_signer';

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
          onClick={onToggleLandmarks}
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

      {/* 16:9 Video Aspect Container (Unmirrored frames processed by MediaPipe; visually mirrored by CSS -scale-x-100) */}
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
              No video frames are recorded, stored, or transmitted.
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
              Initializing browser MediaPipe Tasks and landmark extractor...
            </p>
          </div>
        )}

        {/* State: No Signer In Frame */}
        {isNoSigner && (
          <div
            className="absolute bottom-4 inset-x-4 z-20 flex items-center gap-3 rounded-input border border-warn bg-surface/95 p-3 shadow-md"
            role="alert"
          >
            <div className="rounded-full bg-warn-bg p-2 text-warn shrink-0">
              <UserX className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs font-bold text-ink">
                Step into the frame
              </p>
              <p className="text-xs text-ink-muted">
                {signerNotice || 'Shoulders or hands not clearly detected in camera view.'}
              </p>
            </div>
          </div>
        )}

        {/* Live Webcam Stream (Mirrored visually with CSS only) */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover -scale-x-100"
        />

        {/* Real Skeletal Overlay Canvas (Mirrored visually with CSS only) */}
        {canvasRef && (
          <canvas
            ref={canvasRef}
            className={`pointer-events-none absolute inset-0 h-full w-full object-cover -scale-x-100 ${
              !showLandmarks ? 'hidden' : ''
            }`}
          />
        )}

        {/* State 4: Recognising / Live Streaming Indicator */}
        {uiState === 'recognising' && (
          <div
            className="absolute top-4 left-4 z-10 flex items-center gap-2 rounded-input border border-border bg-surface px-3 py-1.5 text-xs font-bold text-accent shadow-sm"
            role="status"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent"></span>
            </span>
            <span>Signer detected · Tracking live</span>
          </div>
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
