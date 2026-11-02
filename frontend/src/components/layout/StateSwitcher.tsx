import React from 'react';
import { UIState } from '../../types';

interface StateSwitcherProps {
  currentState: UIState;
  onStateSelect: (state: UIState) => void;
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
];

export const StateSwitcher: React.FC<StateSwitcherProps> = ({
  currentState,
  onStateSelect,
}) => {
  return (
    <nav
      className="border-b border-border bg-surface px-6 py-2"
      aria-label="UI state inspection switcher"
    >
      <div className="mx-auto flex max-w-7xl items-center gap-2 overflow-x-auto py-1">
        <span className="shrink-0 font-sans text-xs font-bold uppercase tracking-wider text-ink-muted">
          Design State:
        </span>
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
    </nav>
  );
};

