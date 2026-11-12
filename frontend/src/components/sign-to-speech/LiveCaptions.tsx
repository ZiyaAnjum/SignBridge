import React from 'react';
import { AlertCircle, HelpCircle, AlertTriangle, UserX, WifiOff, Loader2 } from 'lucide-react';
import { ConfidenceTier, TopGuess, UIState } from '../../types';

interface LiveCaptionsProps {
  captionText: string;
  translatedText?: string;
  confidence: number;
  confidenceTier: ConfidenceTier;
  topGuesses?: TopGuess[];
  uiState: UIState;
  modelLoaded?: boolean;
  statusNotice?: string | null;
}

export const LiveCaptions: React.FC<LiveCaptionsProps> = ({
  captionText,
  translatedText,
  confidence,
  confidenceTier,
  topGuesses = [],
  uiState,
  modelLoaded = false,
  statusNotice,
}) => {
  const isLowConfidence = uiState === 'low_confidence';
  const isNoSigner = uiState === 'no_signer';
  const isConnecting = uiState === 'connecting';
  const isConnectionLost = uiState === 'error';

  return (
    <div
      className="mt-4 rounded-card border border-border bg-surface p-5"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* 1. Persistent Demo Mode Banner if model is not trained/loaded */}
      {!modelLoaded && (
        <div
          className="mb-4 flex items-center gap-2.5 rounded-input border border-warn bg-warn-bg p-3 text-xs text-ink"
          role="status"
          aria-label="Demo mode: model not trained, predictions are not real"
        >
          <AlertTriangle className="h-4 w-4 text-warn shrink-0" aria-hidden="true" />
          <div>
            <strong className="font-bold text-warn">Demo mode: </strong>
            <span>model not trained, predictions are not real. Train model in ml-service to enable live signing.</span>
          </div>
        </div>
      )}

      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-border pb-2.5">
        <span className="font-sans text-xs font-bold uppercase tracking-wider text-ink-muted">
          Live Caption
        </span>

        {/* Confidence Indicator: Text label ("High", "Medium", "Low") + bar. Never colour alone */}
        {!isLowConfidence && !isNoSigner && !isConnecting && !isConnectionLost && captionText && (
          <div
            className="flex items-center gap-2"
            role="status"
            aria-label={`Confidence: ${confidenceTier} (${Math.round(confidence * 100)} percent)`}
          >
            <span className="text-xs font-semibold text-ink-muted">
              Confidence: <strong className="text-ink">{confidenceTier}</strong> ({Math.round(confidence * 100)}%)
            </span>
            <div className="h-2 w-16 overflow-hidden rounded-input bg-border">
              <div
                className={`h-full transition-all duration-200 ${
                  confidenceTier === 'High'
                    ? 'bg-ok'
                    : confidenceTier === 'Medium'
                    ? 'bg-warn'
                    : 'bg-emergency'
                }`}
                style={{ width: `${Math.max(5, Math.round(confidence * 100))}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* State: No Signer Visible */}
      {isNoSigner && (
        <div
          className="mt-4 flex items-center gap-3 rounded-input border border-warn bg-warn-bg p-4 text-ink"
          role="alert"
        >
          <UserX className="h-5 w-5 text-warn shrink-0" aria-hidden="true" />
          <div>
            <h3 className="font-serif text-base font-bold text-ink">
              Step into the frame
            </h3>
            <p className="mt-0.5 text-xs text-ink-muted">
              {statusNotice || 'Position shoulders and hands clearly in front of the camera.'}
            </p>
          </div>
        </div>
      )}

      {/* State: Connecting */}
      {isConnecting && (
        <div className="mt-4 flex items-center gap-3 py-3 text-ink-muted">
          <Loader2 className="h-5 w-5 animate-spin text-accent" aria-hidden="true" />
          <span className="text-sm font-semibold">Connecting to recognition service...</span>
        </div>
      )}

      {/* State: Connection Lost */}
      {isConnectionLost && (
        <div
          className="mt-4 flex items-center gap-3 rounded-input border border-emergency bg-emergency-bg p-4 text-emergency"
          role="alert"
        >
          <WifiOff className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <h3 className="font-serif text-base font-bold">
              Connection lost
            </h3>
            <p className="mt-0.5 text-xs">
              Reconnecting to WebSocket (ws://127.0.0.1:8000/ws/landmarks)...
            </p>
          </div>
        </div>
      )}

      {/* State: Low Confidence Prompt with Top 2 Guesses */}
      {!isNoSigner && !isConnecting && !isConnectionLost && isLowConfidence && (
        <div
          className="mt-4 rounded-input border border-warn bg-warn-bg p-4 text-ink"
          role="alert"
        >
          <div className="flex items-center gap-2 text-warn">
            <HelpCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
            <h3 className="font-serif text-base font-bold">
              Not sure. Please sign again.
            </h3>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            The sign was ambiguous or partially out of view. Possible candidate matches:
          </p>

          {topGuesses.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {topGuesses.slice(0, 2).map((guess, idx) => (
                <div
                  key={guess.label}
                  className="flex items-center gap-2 rounded-input border border-border bg-surface px-3 py-1.5 text-xs font-semibold"
                >
                  <span className="text-ink-muted">#{idx + 1}</span>
                  <span className="text-ink font-bold">{guess.label}</span>
                  <span className="text-ink-muted">({Math.round(guess.confidence * 100)}%)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Standard Recognized Live Caption Display (28-32px, weight 600, line-height 1.25 per DESIGN.md) */}
      {!isNoSigner && !isConnecting && !isConnectionLost && !isLowConfidence && (
        <div className="mt-4">
          <div className="min-h-[48px] flex items-center">
            {captionText ? (
              <p className="font-sans text-[28px] md:text-[32px] font-semibold leading-[1.25] text-ink animate-caption-pulse">
                &ldquo;{captionText}&rdquo;
              </p>
            ) : (
              <p className="font-sans text-base italic text-ink-muted">
                Waiting for sign gestures...
              </p>
            )}
          </div>

          {/* Multilingual Subtitle Output */}
          {translatedText && captionText && (
            <p className="mt-2 font-sans text-sm text-ink-muted">
              Translation: <span className="font-semibold text-ink">{translatedText}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};
