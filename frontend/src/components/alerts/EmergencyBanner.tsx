import React from 'react';
import { AlertTriangle, BellRing, X } from 'lucide-react';

interface EmergencyBannerProps {
  onDismiss: () => void;
  scenarioText?: string;
}

export const EmergencyBanner: React.FC<EmergencyBannerProps> = ({
  onDismiss,
  scenarioText = 'Patient signed: "Emergency / Severe Pain"',
}) => {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="w-full border-b-2 border-emergency bg-emergency-bg px-6 py-4 animate-fade-in"
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
        {/* Urgent Icon & Text */}
        <div className="flex items-center gap-3">
          <div className="rounded-input bg-emergency p-2 text-surface">
            <AlertTriangle className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif text-lg font-bold text-emergency">
                Emergency Signed
              </span>
              <span className="inline-flex items-center gap-1 rounded-input border border-emergency/30 bg-surface px-2 py-0.5 text-xs font-bold text-emergency">
                <BellRing className="h-3.5 w-3.5" aria-hidden="true" />
                Staff Alert Active
              </span>
            </div>
            <p className="font-sans text-sm font-semibold text-ink mt-0.5">
              {scenarioText}
            </p>
          </div>
        </div>

        {/* Immediate Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              alert('Emergency responder team dispatched to this counter.');
            }}
            className="flex items-center gap-2 rounded-input bg-emergency px-4 py-2.5 text-sm font-bold text-surface hover:opacity-95 min-h-[48px]"
          >
            <span>Dispatch Triage / Security</span>
          </button>

          <button
            type="button"
            onClick={onDismiss}
            className="flex items-center gap-2 rounded-input border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-ink hover:bg-bg min-h-[48px]"
          >
            <X className="h-4 w-4" aria-hidden="true" />
            <span>Dismiss</span>
          </button>
        </div>
      </div>
    </div>
  );
};

