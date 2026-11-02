import React from 'react';
import { Check, Edit3, Volume2 } from 'lucide-react';

interface SentenceConfirmationProps {
  sentence: string;
  onConfirm: () => void;
  onFix: () => void;
}

export const SentenceConfirmation: React.FC<SentenceConfirmationProps> = ({
  sentence,
  onConfirm,
  onFix,
}) => {
  return (
    <div
      className="mb-4 rounded-card border-2 border-accent bg-surface p-4"
      role="region"
      aria-label="Sentence confirmation awaiting speech"
    >
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <span className="font-sans text-xs font-bold uppercase tracking-wider text-accent">
          Sentence Built · Ready to Speak
        </span>
        <span className="text-xs text-ink-muted">Awaiting confirmation</span>
      </div>

      <div className="my-3">
        <p className="font-sans text-lg font-semibold text-ink leading-snug">
          &ldquo;{sentence}&rdquo;
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onConfirm}
          className="flex-1 flex items-center justify-center gap-2 rounded-input bg-accent px-4 py-3 text-sm font-bold text-accent-ink hover:opacity-95 min-h-[48px]"
        >
          <Check className="h-4 w-4" aria-hidden="true" />
          <Volume2 className="h-4 w-4" aria-hidden="true" />
          <span>Confirm & Speak</span>
        </button>

        <button
          type="button"
          onClick={onFix}
          className="flex items-center justify-center gap-2 rounded-input border border-border bg-surface px-4 py-3 text-sm font-semibold text-ink hover:bg-bg min-h-[48px]"
        >
          <Edit3 className="h-4 w-4 text-ink-muted" aria-hidden="true" />
          <span>Fix</span>
        </button>
      </div>
    </div>
  );
};

