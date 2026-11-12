import React from 'react';
import { Check, Undo2, Trash2, Volume2, AlertCircle, Info } from 'lucide-react';

interface SentenceConfirmationProps {
  sentence: string;
  translatedSentence?: string;
  words?: string[];
  modelLoaded?: boolean;
  voiceNotice?: string | null;
  onConfirm: () => void;
  onFix: () => void;
  onClear?: () => void;
}

export const SentenceConfirmation: React.FC<SentenceConfirmationProps> = ({
  sentence,
  translatedSentence,
  words = [],
  modelLoaded = true,
  voiceNotice,
  onConfirm,
  onFix,
  onClear,
}) => {
  return (
    <div
      className="mb-4 rounded-card border-2 border-accent bg-surface p-5 shadow-sm"
      role="region"
      aria-label="Sentence draft awaiting confirmation"
    >
      <div className="flex items-center justify-between pb-2.5 border-b border-border">
        <span className="font-sans text-xs font-bold uppercase tracking-wider text-accent flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
          Sentence Draft ({words.length > 0 ? words.length : 1} words)
        </span>
        <span className="text-xs text-ink-muted">Awaiting confirmation</span>
      </div>

      {/* Accumulated word chips */}
      {words.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {words.map((w, idx) => (
            <span
              key={`${w}-${idx}`}
              className="rounded-input border border-border bg-bg px-2.5 py-1 text-xs font-semibold text-ink"
            >
              {w}
            </span>
          ))}
        </div>
      )}

      {/* Full built sentence */}
      <div className="my-3">
        <p className="font-sans text-xl font-semibold text-ink leading-snug">
          &ldquo;{sentence}&rdquo;
        </p>
        {translatedSentence && (
          <p className="mt-1 text-sm text-ink-muted">
            Translation: <span className="font-semibold text-ink">{translatedSentence}</span>
          </p>
        )}
      </div>

      {/* Voice notice if browser voice is missing */}
      {voiceNotice && (
        <div className="mb-3 flex items-center gap-2 rounded-input border border-border bg-bg p-2.5 text-xs text-ink-muted">
          <Info className="h-4 w-4 text-ink-muted shrink-0" aria-hidden="true" />
          <span>{voiceNotice}</span>
        </div>
      )}

      {/* Demo mode warning: do not speak or add to timeline */}
      {!modelLoaded && (
        <div className="mb-3 flex items-center gap-2 rounded-input border border-warn bg-warn-bg p-2.5 text-xs text-ink">
          <AlertCircle className="h-4 w-4 text-warn shrink-0" aria-hidden="true" />
          <span>
            <strong className="font-bold">Demo mode: </strong>
            Predictions are not real. Confirm & Speak is locked until a trained model is loaded.
          </span>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={!modelLoaded}
          className="flex-1 flex items-center justify-center gap-2 rounded-input bg-accent px-4 py-3 text-sm font-bold text-accent-ink hover:opacity-95 disabled:opacity-40 min-h-[48px]"
        >
          <Check className="h-4 w-4" aria-hidden="true" />
          <Volume2 className="h-4 w-4" aria-hidden="true" />
          <span>Confirm & Speak</span>
        </button>

        <button
          type="button"
          onClick={onFix}
          className="flex items-center justify-center gap-1.5 rounded-input border border-border bg-surface px-4 py-3 text-sm font-semibold text-ink hover:bg-bg min-h-[48px]"
          title="Remove last word from draft"
        >
          <Undo2 className="h-4 w-4 text-ink-muted" aria-hidden="true" />
          <span>Fix</span>
        </button>

        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="flex items-center justify-center gap-1.5 rounded-input border border-border bg-surface px-3 py-3 text-sm font-semibold text-ink-muted hover:bg-bg hover:text-emergency min-h-[48px]"
            title="Clear entire draft"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Clear draft</span>
          </button>
        )}
      </div>
    </div>
  );
};
