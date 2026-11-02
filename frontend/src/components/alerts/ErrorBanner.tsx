import React from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';

interface ErrorBannerProps {
  onRetry: () => void;
  message?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  onRetry,
  message = 'Connection lost. Cannot reach recognition service at ws://localhost:8000/ws/landmarks.',
}) => {
  return (
    <div
      role="alert"
      className="w-full border-b border-border bg-warn-bg px-6 py-3"
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <WifiOff className="h-5 w-5 text-warn" aria-hidden="true" />
          <p className="font-sans text-sm font-semibold text-ink">
            {message}
          </p>
        </div>

        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 rounded-input border border-border bg-surface px-4 py-2 text-xs font-bold text-ink hover:bg-bg min-h-[36px]"
        >
          <RefreshCw className="h-3.5 w-3.5 text-accent" aria-hidden="true" />
          <span>Retry Connection</span>
        </button>
      </div>
    </div>
  );
};

