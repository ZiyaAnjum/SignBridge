import React from 'react';
import { UIState } from '../../types';
import { Wrench } from 'lucide-react';

interface StateSwitcherProps {
  currentState: UIState;
  onStateSelect: (state: UIState) => void;
  isDevMode: boolean;
  onToggleDevMode: () => void;
}

const STATES: { id: UIState; label: string }[] = [
  { id: 'empty', label: '1. Empty' },
  { id: 'camera_denied', label: '2. Camera Denied' },
  { id: 'loading_model', label: '3. Loading Model' },
  { id: 'recognising', label: '4. Recognising' },
  { id: 'low_confidence', label: '5. Low Confidence' },
  { id: 'confirmed_sentence', label: '6. Sentence Awaiting Speech' },
  { id: 'error', label: '7. Error / Offline' },
  { id: 'emergency', label: '8. Emergency' },
  { id: 'no_signer', label: '9. No Signer' },
];

export const StateSwitcher: React.FC<StateSwitcherProps> = ({
  currentState,
  onStateSelect,
  isDevMode,
  onToggleDevMode,
}) => {
  if (!isDevMode) return null;

  return (
    <nav
      className="border-b border-border bg-surface px-6 py-2"
      aria-label="UI state inspection switcher"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 overflow-x-auto py-1">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs font-bold text-accent">
            <Wrench className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="uppercase tracking-wider">Dev Inspector:</span>
          </div>
          <div className="flex items-center gap-1.5 flex-nowrap">
            {STATES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onStateSelect(item.id)}
                className={`shrink-0 rounded-input px-2.5 py-1 text-xs font-medium transition-colors ${
                  currentState === item.id
                    ? 'bg-ink text-surface font-semibold'
                    : 'bg-bg text-ink border border-border hover:bg-surface'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={onToggleDevMode}
          className="shrink-0 text-xs text-ink-muted hover:text-ink underline"
          title="Toggle dev mode shortcut: Shift+D"
        >
          Hide Dev Bar (Shift+D)
        </button>
      </div>
    </nav>
  );
};
