import React from 'react';
import { AlertCircle, HelpCircle } from 'lucide-react';
import { ConfidenceTier, TopGuess, UIState } from '../../types';

interface LiveCaptionsProps {
  captionText: string;
  translatedText?: string;
  confidence: number;
  confidenceTier: ConfidenceTier;
  topGuesses?: TopGuess[];
  uiState: UIState;
}

export const LiveCaptions: React.FC<LiveCaptionsProps> = ({
  captionText,
  translatedText,
  confidence,
  confidenceTier,
  topGuesses = [
    { label: 'doctor', confidence: 0.42 },
    { label: 'nurse', confidence: 0.38 },
  ],
  uiState,
}) => {
  const isLowConfidence = uiState === 'low_confidence';

  return (
    <div
      className="mt-4 rounded-card border border-border bg-surface p-4"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center justify-between border-b border-border pb-2">
        <span className="font-sans text-xs font-bold uppercase tracking-wider text-ink-muted">
          Live Caption
        </span>

        {/* Confidence Indicator: Text label ("High", "Medium", "Low") + bar. Not colour only */}
        {!isLowConfidence && captionText && (
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
                style={{ width: `${Math.round(confidence * 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* State 5: Low Confidence Prompt */}
      {isLowConfidence ? (
        <div
          className="mt-3 rounded-input border border-warn bg-warn-bg p-4 text-ink"
          role="alert"
        >
          <div className="flex items-center gap-2 text-warn">
            <HelpCircle className="h-5 w-5 shrink-0" aria-hidden="true" />
            <h3 className="font-serif text-base font-bold">
              Not sure. Please sign again.
            </h3>
          </div>
          <p className="mt-1 text-xs text-ink-muted">
            The gesture was ambiguous or partially out of view. Possible matches:
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {topGuesses.map((guess, idx) => (
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
        </div>
      ) : (
        /* Standard Live Caption Display */
        <div className="mt-3">
          <div className="min-h-[42px] flex items-center">
            {captionText ? (
              <p className="font-sans text-xl font-semibold leading-[1.3] text-ink animate-caption-pulse">
                &ldquo;{captionText}&rdquo;
              </p>
            ) : (
              <p className="font-sans text-sm italic text-ink-muted">
                Waiting for sign gestures...
              </p>
            )}
          </div>

          {/* Multilingual Subtitle Output */}
          {translatedText && (
            <p className="mt-1 font-sans text-sm text-ink-muted">
              Translation: <span className="font-medium text-ink">{translatedText}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

